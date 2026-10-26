"""
Prépare les données MIRFLICKR-1M pour l'indexation.

  data/mirflickr/
    ├── tags.zip                         → 1 fichier texte par image (mots-clés)
    ├── license.zip                      → licence, propriétaire, titre, URL Flickr
    ├── features_edgehistogram.zip       → MPEG-7 Edge Histogram (par lots de 1000)
    └── features_homogeneoustexture.zip  → MPEG-7 Homogeneous Texture (par lots de 1000)

Chaque archive est inspectée puis convertie en format exploitable :
  - data/mirflickr/text.jsonl   : {id, title, tags, owner, url}  (streamable → ES bulk)
  - data/mirflickr/edge.npy     : np.memmap (float32, N × D_edge)
  - data/mirflickr/homo.npy     : np.memmap (float32, N × D_homo)
  - data/mirflickr/ids.npy      : np.int32 (indice ligne → photo_id MIRFLICKR 1..N)

Comme la documentation du site est muette sur le format exact, le script
sonde chaque zip (`--inspect`) et imprime des échantillons avant parsing.
"""

import argparse
import json
import os
import re
import sys
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
# En conteneur : /app/data (bind-mount), sinon ../data côté hôte.
DATA = Path(os.environ.get("DATA_DIR",
                           str(HERE.parent / "data"))) / "mirflickr"


# ---------------------------------------------------------------------------
# Inspection : affiche une liste d'exemples pour chaque archive
# ---------------------------------------------------------------------------

def inspect_zip(zp: Path, n_names: int = 6, n_bytes: int = 400):
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        print(f"\n== {zp.name} ({len(names):,} entrées)")
        for name in names[:n_names]:
            print(f"  - {name}")
        if len(names) > n_names:
            print(f"  ... (+{len(names) - n_names:,} autres)")
        # Un échantillon textuel du premier fichier non-vide
        for name in names[:50]:
            try:
                data = z.read(name)
            except KeyError:
                continue
            if not data:
                continue
            try:
                print(f"  sample ({name}, {len(data)} octets):")
                print("    " + data[:n_bytes].decode("utf-8", errors="replace")
                      .replace("\n", "\n    "))
            except Exception:
                print(f"  binary ({len(data)} octets)")
            break


def inspect_all():
    for name in ("tags.zip", "license.zip",
                 "features_edgehistogram.zip",
                 "features_homogeneoustexture.zip"):
        p = DATA / name
        if p.exists():
            inspect_zip(p)
        else:
            print(f"  (absent) {p}")


# ---------------------------------------------------------------------------
# Parsers (ajustés après inspection selon le format réel du site)
# ---------------------------------------------------------------------------

PHOTO_ID_RE = re.compile(r"(\d+)")


def _photo_id(name: str) -> int:
    m = PHOTO_ID_RE.search(os.path.basename(name))
    return int(m.group(1)) if m else -1


def iter_tags(zp: Path):
    """1 fichier texte par image, une ligne = un tag."""
    with zipfile.ZipFile(zp) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            pid = _photo_id(info.filename)
            if pid < 0:
                continue
            text = z.read(info).decode("utf-8", errors="replace")
            tags = [t.strip() for t in text.splitlines() if t.strip()]
            yield pid, tags


def iter_license(zp: Path):
    """
    Fichier(s) tabulaire(s). Chaque ligne décrit une photo ; la structure exacte
    est détectée par inspection. Convention retenue (sera adaptée si besoin) :
    des colonnes séparées par des tabulations, incluant id, owner, title et url.
    """
    with zipfile.ZipFile(zp) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            data = z.read(info).decode("utf-8", errors="replace")
            for line in data.splitlines():
                if not line.strip():
                    continue
                parts = line.split("\t") if "\t" in line else line.split(",")
                yield info.filename, parts


# ---------------------------------------------------------------------------
# Construction d'index (après que les parsers soient confirmés)
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspect", action="store_true",
                    help="N'extrait rien, imprime juste des exemples par archive.")
    args = ap.parse_args()
    if args.inspect or not any((DATA / f).exists() for f in (
            "features_edgehistogram.zip", "features_homogeneoustexture.zip")):
        inspect_all()
        return
    print("Build complet : à implémenter une fois le format confirmé.")
    print("Lancer d'abord : python build_mirflickr.py --inspect")


if __name__ == "__main__":
    main()
