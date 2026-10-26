"""
Recherche visuelle sur MIRFLICKR-1M via les descripteurs MPEG-7 fournis.

Les descripteurs sont stockés en memmap (data/mirflickr/{edge,homo}.npy) :
le chargement est quasi gratuit, l'OS pagine à la demande.

Recherche :
  - VP-Tree si data/mirflickr/{name}_vptree.npz existe (construit hors-ligne).
  - Sinon : scan linéaire par blocs, parallèle sur les coeurs CPU disponibles
    (numpy relâche le GIL dans np.abs/sum sur de grands tableaux).
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from config import DATA_DIR
from vptree import VPTree, linear_search

MIR_DIR = Path(DATA_DIR) / "mirflickr"

# Dimensions des descripteurs MPEG-7 fournis par MIRFLICKR-1M (une seule source
# de vérité, partagée avec scripts/index_mirflickr.py). Le meta.json écrit à
# l'indexation fait foi ; ces valeurs ne servent que s'il est absent.
DIMS = {"edge": 150, "homo": 43}


class MirflickrDescriptor:
    def __init__(self, name: str):
        self.name = name
        meta_path = MIR_DIR / f"{name}.meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            self.N, self.dims = int(meta["N"]), int(meta["dims"])
        else:
            self.dims = DIMS[name]
            self.N = 1_000_001
        expected = self.N * self.dims * 4
        actual = (MIR_DIR / f"{name}.npy").stat().st_size
        if actual != expected:
            raise ValueError(
                f"{name}.npy : {actual} octets, attendu {expected} "
                f"({self.N} × {self.dims} float32). Relancez index_mirflickr.py."
            )
        self.X = np.memmap(MIR_DIR / f"{name}.npy", dtype=np.float32, mode="r",
                           shape=(self.N, self.dims))
        self.tree = None
        tp = MIR_DIR / f"{name}_vptree.npz"
        if tp.exists():
            self.tree = VPTree.load(tp, self.X)

    def vector(self, photo_id: int) -> np.ndarray:
        if 0 <= photo_id < self.N:
            return np.asarray(self.X[photo_id], dtype=np.float32)
        raise IndexError(f"photo_id {photo_id} hors bornes")

    def search(self, q: np.ndarray, k: int = 10,
               exclude: Optional[int] = None) -> dict:
        ex = int(exclude) if exclude is not None else -1
        if self.tree is not None:
            res, s = self.tree.search(q, k=k, exclude=ex)
        else:
            res, s = linear_search(self.X, q, k=k, exclude=ex)
        return {
            "results": [{"photo_id": int(i), "distance": float(d),
                         "score": float(1.0 / (1.0 + d))}
                        for d, i in res],
            **s,
        }


_registry: Dict[str, MirflickrDescriptor] = {}


def available() -> List[str]:
    return [n for n in ("edge", "homo") if (MIR_DIR / f"{n}.npy").exists()]


def get(name: str) -> MirflickrDescriptor:
    if name not in _registry:
        _registry[name] = MirflickrDescriptor(name)
    return _registry[name]
