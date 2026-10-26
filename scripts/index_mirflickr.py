"""
Importe MIRFLICKR-1M dans le moteur de recherche.

Entrées (data/mirflickr/*.zip) :
  - tags.zip      → tags/<bucket>/<id>.txt   (un tag par ligne)
  - license.zip   → license/<bucket>/<id>.txt (clé " : " valeur)
  - features_edgehistogram.zip      → MPEG-7 Edge Histogram, 1 fichier par image
  - features_homogeneoustexture.zip → MPEG-7 Homogeneous Texture, idem

Sorties :
  - index Elasticsearch 'mirflickr' : {photo_id, title, tags, owner, url, license}
  - data/mirflickr/edge.npy  : np.memmap float32 (N, 150)
  - data/mirflickr/homo.npy  : np.memmap float32 (N, 43)
  (dimensions détectées sur les données, écrites dans {edge,homo}.meta.json)
  - data/mirflickr/ids.npy   : np.int64 (ordre des lignes → photo_id MIRFLICKR)
  - data/mirflickr/edge_vptree.npz / homo_vptree.npz

Chaque étape est optionnelle : --steps tags,license,text,mpeg7,vptree
"""

import argparse
import io
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))

from config import DATA_DIR
from es_client import get_es
from mirflickr_index import DIMS

MIR_DIR = Path(DATA_DIR) / "mirflickr"
MIRFLICKR_INDEX = "mirflickr"

PHOTO_ID_RE = re.compile(r"/(\d+)\.txt$")


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def _photo_id(name: str) -> int:
    m = PHOTO_ID_RE.search(name) or re.search(r"(\d+)\.(txt|dat|xml|bin|desc)$",
                                              name)
    return int(m.group(1)) if m else -1


def _flickr_url(photo_id: int, filename: str = None) -> str:
    # MIRFLICKR dérive le nom de fichier de l'image hôte (im{photo_id}.jpg) mais
    # ne stocke pas farm/server/secret : on l'omet (champ 'url' local).
    return f"im{photo_id}.jpg"


# ---------------------------------------------------------------------------
# Parsing des archives texte
# ---------------------------------------------------------------------------

def iter_text_zip(zp: Path, parser) -> Iterator[Tuple[int, dict]]:
    """
    Itère sur une archive de forme <dossier>/<bucket>/<id>.txt et applique `parser`
    à chaque contenu. parser(text) → dict.
    """
    with zipfile.ZipFile(zp) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            pid = _photo_id(info.filename)
            if pid < 0:
                continue
            text = z.read(info).decode("utf-8", errors="replace")
            yield pid, parser(text)


def parse_tags(text: str) -> dict:
    tags = [t.strip() for t in text.splitlines() if t.strip()]
    return {"tags": tags}


LICENSE_RE = re.compile(r"^([^:]+?)\s+:\s*(.*)$")
LICENSE_MAP = {
    "picture title": "title",
    "owner username": "owner",
    "owner id": "owner_id",
    "license": "license",
    "license url": "license_url",
    "date uploaded": "date_uploaded",
}


def parse_license(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        m = LICENSE_RE.match(line.strip())
        if not m:
            continue
        key = m.group(1).strip().lower()
        value = m.group(2).strip()
        if key in LICENSE_MAP:
            out[LICENSE_MAP[key]] = value
    return out


# ---------------------------------------------------------------------------
# Indexation Elasticsearch
# ---------------------------------------------------------------------------

MIRFLICKR_MAPPING = {
    "mappings": {
        "properties": {
            "photo_id":     {"type": "long"},
            "title":        {"type": "text"},
            "tags":         {"type": "text"},
            "owner":        {"type": "keyword"},
            "owner_id":     {"type": "keyword"},
            "license":      {"type": "keyword"},
            "license_url":  {"type": "keyword"},
            "date_uploaded": {"type": "keyword"},
            "url":          {"type": "keyword"},
        }
    }
}


def ensure_index(es, name=MIRFLICKR_INDEX):
    if not es.indices.exists(index=name):
        es.indices.create(index=name, body=MIRFLICKR_MAPPING)
        print(f"Index '{name}' créé.")


def _merge_streams(tags_iter, license_iter) -> Iterator[dict]:
    """Jointure par photo_id, en gardant chaque source en flux."""
    license_by_id: dict = {}
    for pid, lic in license_iter:
        license_by_id[pid] = lic
    for pid, tg in tags_iter:
        lic = license_by_id.pop(pid, {})
        yield {
            "_index": MIRFLICKR_INDEX,
            "_id": pid,
            "_source": {
                "photo_id": pid,
                "title": lic.get("title", ""),
                "tags": " ".join(tg.get("tags", [])),
                "owner": lic.get("owner", ""),
                "owner_id": lic.get("owner_id", ""),
                "license": lic.get("license", ""),
                "license_url": lic.get("license_url", ""),
                "date_uploaded": lic.get("date_uploaded", ""),
                "url": _flickr_url(pid),
            },
        }
    for pid, lic in license_by_id.items():
        yield {
            "_index": MIRFLICKR_INDEX, "_id": pid,
            "_source": {"photo_id": pid, **lic, "url": _flickr_url(pid)},
        }


def step_text(es):
    """Indexe tags + license dans ES."""
    from elasticsearch import helpers
    ensure_index(es)
    tags_zp = MIR_DIR / "tags.zip"
    lic_zp = MIR_DIR / "license.zip"
    if not tags_zp.exists() or not lic_zp.exists():
        raise FileNotFoundError("tags.zip et license.zip requis.")
    actions = _merge_streams(
        iter_text_zip(tags_zp, parse_tags),
        iter_text_zip(lic_zp, parse_license),
    )
    ok, errs = helpers.bulk(es, actions, chunk_size=2000, request_timeout=120,
                            raise_on_error=False)
    print(f"Indexation : {ok} docs OK, {len(errs) if isinstance(errs, list) else errs} erreurs.")


# ---------------------------------------------------------------------------
# MPEG-7 descriptors
# ---------------------------------------------------------------------------

FLOAT_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


def _parse_floats(data: bytes) -> np.ndarray:
    """
    Extrait tous les nombres d'un contenu, qu'il soit texte (CSV/espaces), XML
    (<component>…</component>) ou binaire float32. On essaie d'abord le binaire
    si la taille est multiple de 4 et donne une dimension connue.
    """
    # Texte / XML : extraction regex, robuste au format
    try:
        txt = data.decode("utf-8", errors="replace")
        vals = [float(m.group()) for m in FLOAT_RE.finditer(txt)]
        if vals:
            return np.asarray(vals, dtype=np.float32)
    except Exception:
        pass
    # Binaire float32
    return np.frombuffer(data, dtype="<f4")


def _iter_feature_zip(zp: Path) -> Iterator[Tuple[int, np.ndarray]]:
    with zipfile.ZipFile(zp) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            pid = _photo_id(info.filename)
            if pid < 0:
                continue
            yield pid, _parse_floats(z.read(info))


def step_mpeg7(name: str, zp: Path, dims_hint: int = 0):
    """
    Décompresse les descripteurs MPEG-7 vers un memmap float32 (N, D).
    N = max_id + 1 ; les photos manquantes → vecteur nul (plus simple pour l'index).
    """
    if not zp.exists():
        print(f"  (absent) {zp} — étape '{name}' sautée.")
        return
    probe_pid, probe_vec = next(_iter_feature_zip(zp))
    D = probe_vec.size if probe_vec.size else dims_hint
    N = 1_000_001  # MIRFLICKR-1M : ids contigus 0..999_999 avec marge pour "im1000000.jpg"
    print(f"[{name}] probe id={probe_pid}, dims={D}, allocation ({N:,}, {D}) = {N*D*4/2**20:.0f} Mo")
    out = np.memmap(MIR_DIR / f"{name}.npy", dtype=np.float32, mode="w+",
                    shape=(N, D))
    t0 = time.perf_counter()
    seen = 0
    for pid, vec in _iter_feature_zip(zp):
        if vec.size != D:  # tronque / pad : on garde D fixe
            v = np.zeros(D, dtype=np.float32)
            v[:min(D, vec.size)] = vec[:D]
            vec = v
        if 0 <= pid < N:
            out[pid] = vec
            seen += 1
            if seen % 100000 == 0:
                print(f"  [{name}] {seen:,} ({(time.perf_counter() - t0):.0f} s)")
    out.flush()
    (MIR_DIR / f"{name}.meta.json").write_text(json.dumps({"N": N, "dims": D,
                                                           "zp": str(zp.name),
                                                           "seen": seen}))
    print(f"[{name}] {seen:,} descripteurs écrits → {MIR_DIR}/{name}.npy")


def step_vptree(name: str):
    """Construit un VP-Tree sur un memmap MPEG-7."""
    from vptree import VPTree
    meta_path = MIR_DIR / f"{name}.meta.json"
    if not meta_path.exists():
        print(f"[{name}] pas de descripteurs — étape 'vptree' sautée.")
        return
    meta = json.loads(meta_path.read_text())
    X = np.memmap(MIR_DIR / f"{name}.npy", dtype=np.float32, mode="r",
                  shape=(meta["N"], meta["dims"]))
    t0 = time.perf_counter()
    tree = VPTree.build(X, leaf_size=256, chunk=50_000)
    tree.save(MIR_DIR / f"{name}_vptree.npz")
    print(f"[{name}] VP-Tree ({tree.n_nodes} nœuds) en {time.perf_counter() - t0:.1f} s")


# ---------------------------------------------------------------------------
# Entrée
# ---------------------------------------------------------------------------

STEPS = {"text", "edge", "homo", "vptree"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default="text,edge,homo,vptree",
                    help="Sous-ensemble de : " + ",".join(sorted(STEPS)))
    args = ap.parse_args()
    steps = {s.strip() for s in args.steps.split(",")}
    MIR_DIR.mkdir(parents=True, exist_ok=True)

    if "text" in steps:
        step_text(get_es())
    if "edge" in steps:
        step_mpeg7("edge", MIR_DIR / "features_edgehistogram.zip",
                   dims_hint=DIMS["edge"])
    if "homo" in steps:
        step_mpeg7("homo", MIR_DIR / "features_homogeneoustexture.zip",
                   dims_hint=DIMS["homo"])
    if "vptree" in steps:
        step_vptree("edge")
        step_vptree("homo")


if __name__ == "__main__":
    main()
