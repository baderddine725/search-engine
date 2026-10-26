"""
Service de recherche basée descripteurs (color / lbp / hog) via VP-Tree.

Chargé une fois par processus. Chaque descripteur a son propre VP-Tree.
Pour une requête multi-descripteurs, chaque arbre est interrogé puis les
résultats sont fusionnés : les distances sont ramenées sur [0,1] en divisant
par la distance L1 maximale théorique entre deux histogrammes L1-normalisés
(c'est-à-dire 2), puis combinées par somme pondérée.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from descriptors import DESCRIPTORS, extract
from vptree import VPTree, linear_search
from config import DATA_DIR as _CFG_DATA_DIR

INDEX_DIR = Path(_CFG_DATA_DIR) / "descriptors"


class DescriptorIndex:
    """Enveloppe autour d'un VP-Tree pour un descripteur."""

    def __init__(self, name: str):
        self.name = name
        d = INDEX_DIR / name
        self.X = np.load(d / "features.npy", mmap_mode="r")
        self.paths: List[str] = json.loads((d / "paths.json").read_text())
        self.classes: List[str] = json.loads((d / "classes.json").read_text())
        self.tree = VPTree.load(d / "vptree.npz", self.X)
        self.path_to_idx = {p: i for i, p in enumerate(self.paths)}

    def size(self) -> int:
        return len(self.paths)

    def vector(self, image_path: str) -> Optional[np.ndarray]:
        i = self.path_to_idx.get(image_path)
        return None if i is None else np.asarray(self.X[i], dtype=np.float32)

    def search(self, q: np.ndarray, k: int, exclude: Optional[str] = None,
               exact: bool = False) -> Tuple[List[Tuple[float, int]], dict]:
        ex = self.path_to_idx.get(exclude, -1) if exclude else -1
        if exact:
            return linear_search(self.X, q, k=k, exclude=ex)
        return self.tree.search(q, k=k, exclude=ex)


# ---------------------------------------------------------------------------
# Registre global
# ---------------------------------------------------------------------------

_registry: Dict[str, DescriptorIndex] = {}


def available() -> List[str]:
    """Descripteurs dont les index existent sur disque."""
    return [n for n in DESCRIPTORS if (INDEX_DIR / n / "features.npy").exists()]


def load_all() -> Dict[str, DescriptorIndex]:
    for n in available():
        if n not in _registry:
            _registry[n] = DescriptorIndex(n)
    return _registry


def get(name: str) -> DescriptorIndex:
    if name not in _registry:
        _registry[name] = DescriptorIndex(name)
    return _registry[name]


# ---------------------------------------------------------------------------
# Recherche multi-descripteurs : union + re-ranking
# ---------------------------------------------------------------------------

L1_MAX = 2.0  # distance L1 maximale entre deux vecteurs L1-normalisés


def _rank_combined(indices: List[DescriptorIndex],
                   queries: List[np.ndarray],
                   weights: List[float],
                   k: int,
                   exclude: Optional[str],
                   candidates: int,
                   exact: bool) -> Tuple[List[dict], dict]:
    """
    Union des top-`candidates` de chaque descripteur, puis re-rank en calculant
    la vraie distance combinée pondérée sur chaque candidat (distances issues
    directement des features, pas des bornes de l'arbre).
    """
    t0 = time.perf_counter()
    pool: Dict[int, None] = {}
    per_descriptor_stats = {}
    for idx, q, w in zip(indices, queries, weights):
        if w <= 0:
            continue
        res, s = idx.search(q, k=candidates, exclude=exclude, exact=exact)
        per_descriptor_stats[idx.name] = {**s, "weight": w}
        for _, i in res:
            pool[i] = None
    cand = list(pool)
    if not cand:
        return [], {"candidates": 0, "search_ms": (time.perf_counter() - t0) * 1000,
                    "per_descriptor": per_descriptor_stats}
    # Distances exactes sur les candidats, poids normalisés
    total_w = sum(weights) or 1.0
    weights_norm = [w / total_w for w in weights]
    scores = np.zeros(len(cand), dtype=np.float32)
    for idx, q, w in zip(indices, queries, weights_norm):
        rows = np.asarray(idx.X[cand], dtype=np.float32)
        d = np.abs(rows - q).sum(axis=1) / L1_MAX   # ∈ [0,1]
        scores += w * d
    order = np.argsort(scores, kind="stable")[:k]
    paths = indices[0].paths
    classes = indices[0].classes
    results = [{
        "image_path": paths[cand[i]],
        "class_name": classes[cand[i]],
        "distance": float(scores[i]),
        "score": float(1.0 / (1.0 + scores[i])),
    } for i in order]
    return results, {
        "candidates": len(cand),
        "search_ms": (time.perf_counter() - t0) * 1000,
        "per_descriptor": per_descriptor_stats,
    }


def search(descriptors: List[str],
           weights: Optional[List[float]] = None,
           *,
           image: Optional[Image.Image] = None,
           image_path: Optional[str] = None,
           k: int = 10,
           candidates: int = 100,
           exact: bool = False) -> dict:
    """
    Recherche k-NN selon un ou plusieurs descripteurs.

    - image     : PIL image → extraction en ligne
    - image_path: chemin d'une image indexée → vecteur déjà en RAM
    """
    load_all()
    if not descriptors:
        raise ValueError("Au moins un descripteur est requis.")
    weights = weights or [1.0] * len(descriptors)
    if len(weights) != len(descriptors):
        raise ValueError("weights doit avoir la même longueur que descriptors.")

    indices = [get(n) for n in descriptors]
    queries: List[np.ndarray] = []
    t_extract = 0.0
    for idx in indices:
        if image_path and idx.vector(image_path) is not None:
            queries.append(idx.vector(image_path))
        else:
            if image is None:
                raise ValueError("image ou image_path indexé requis.")
            t0 = time.perf_counter()
            queries.append(extract(image, idx.name))
            t_extract += time.perf_counter() - t0

    if len(descriptors) == 1:
        res, s = indices[0].search(queries[0], k=k, exclude=image_path, exact=exact)
        paths, classes = indices[0].paths, indices[0].classes
        return {
            "results": [{
                "image_path": paths[i], "class_name": classes[i],
                "distance": float(d) / L1_MAX,
                "score": float(1.0 / (1.0 + d / L1_MAX)),
            } for d, i in res],
            "extract_ms": t_extract * 1000,
            "search_ms": s["search_ms"],
            "candidates": s["distances_computed"],
            "pruned_pct": s.get("pruned_pct", 0.0),
            "index": s["index"],
            "per_descriptor": {indices[0].name: s},
        }

    results, stats = _rank_combined(
        indices, queries, weights, k=k, exclude=image_path,
        candidates=max(candidates, 2 * k), exact=exact,
    )
    return {
        "results": results,
        "extract_ms": t_extract * 1000,
        **stats,
        "index": "vptree-combined",
    }
