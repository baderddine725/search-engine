"""
Extraction des descripteurs classiques (color, lbp, hog) sur la base locale et
construction d'un VP-Tree par descripteur.

Sortie dans data/descriptors/<nom>/ :
  - features.npy  : float32 (N, dims), L1-normalisé
  - paths.json    : [image_path, ...]  (classe = premier segment)
  - classes.json  : [class_name, ...]
  - vptree.npz    : arbre construit sur features.npy

Les trois descripteurs ont des dims petites : la recherche VP-Tree reste
instantanée tant que N ≤ ~100 k. Pour 1 M on utilisera un memmap.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))

from config import BDIMAGE_DIR, DATA_DIR, ALLOWED_EXTENSIONS
from descriptors import DESCRIPTORS, extract
from feature_extractor import load_image_from_path
from vptree import VPTree

OUT_ROOT = Path(DATA_DIR) / "descriptors"


def list_dataset():
    items = []
    for cls in sorted(os.listdir(BDIMAGE_DIR)):
        folder = os.path.join(BDIMAGE_DIR, cls)
        if not os.path.isdir(folder):
            continue
        for fn in sorted(os.listdir(folder)):
            if fn.rsplit(".", 1)[-1].lower() in ALLOWED_EXTENSIONS:
                items.append((f"{cls}/{fn}", cls))
    return items


def build_one(name: str, items, dims: int):
    out_dir = OUT_ROOT / name
    out_dir.mkdir(parents=True, exist_ok=True)
    X = np.zeros((len(items), dims), dtype=np.float32)
    paths, classes = [], []
    t0 = time.perf_counter()
    for i, (rel, cls) in enumerate(items):
        img = load_image_from_path(os.path.join(BDIMAGE_DIR, rel))
        X[i] = extract(img, name)
        paths.append(rel); classes.append(cls)
        if (i + 1) % 100 == 0:
            print(f"  [{name}] {i+1}/{len(items)}")
    extract_s = time.perf_counter() - t0
    np.save(out_dir / "features.npy", X)
    (out_dir / "paths.json").write_text(json.dumps(paths))
    (out_dir / "classes.json").write_text(json.dumps(classes))
    t1 = time.perf_counter()
    tree = VPTree.build(X)
    tree.save(out_dir / "vptree.npz")
    print(f"  [{name}] extraction {extract_s:.1f}s, "
          f"VP-Tree {time.perf_counter() - t1:.2f}s, {tree.n_nodes} nœuds")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--descriptors", nargs="+", default=list(DESCRIPTORS),
                    choices=list(DESCRIPTORS))
    args = ap.parse_args()
    items = list_dataset()
    print(f"{len(items)} images.")
    for name in args.descriptors:
        build_one(name, items, DESCRIPTORS[name]["dims"])


if __name__ == "__main__":
    main()
