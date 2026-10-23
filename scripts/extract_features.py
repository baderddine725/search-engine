"""
Extraction des features pour toutes les images de bdimage.

Un CSV par modèle : image_path, class_name, f0, f1, ...
  - features.csv        : InceptionV3 + LBP (2058 dims)
  - features_vgg16.csv  : VGG16 (512 dims)

Usage : python extract_features.py [--model all|inception_lbp|vgg16]
"""

import argparse
import csv
import os
import sys
import time

# Ajouter le backend au path pour importer les modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from config import BDIMAGE_DIR, MODELS, ALLOWED_EXTENSIONS
from evaluation import load_extraction_stats, save_extraction_stats
from feature_extractor import get_extractor, load_image_from_path


def list_dataset():
    """(chemin relatif, classe) pour chaque image de bdimage/<classe>/."""
    classes = sorted(
        d for d in os.listdir(BDIMAGE_DIR)
        if os.path.isdir(os.path.join(BDIMAGE_DIR, d))
    )
    print(f"Classes trouvées : {len(classes)}")
    items = []
    for cls in classes:
        for img_name in sorted(os.listdir(os.path.join(BDIMAGE_DIR, cls))):
            if img_name.rsplit(".", 1)[-1].lower() in ALLOWED_EXTENSIONS:
                items.append((f"{cls}/{img_name}", cls))
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="all", choices=["all", *MODELS])
    args = parser.parse_args()
    models = list(MODELS) if args.model == "all" else [args.model]

    extractors = {m: get_extractor(m) for m in models}
    files = {m: open(MODELS[m]["features_csv"], "w", newline="") for m in models}
    writers = {m: csv.writer(f) for m, f in files.items()}
    for m in models:
        writers[m].writerow(
            ["image_path", "class_name"] + [f"f{i}" for i in range(MODELS[m]["dims"])]
        )

    elapsed = {m: 0.0 for m in models}
    total = 0
    try:
        for rel_path, cls in list_dataset():
            try:
                img = load_image_from_path(os.path.join(BDIMAGE_DIR, rel_path))
                for m in models:
                    t0 = time.perf_counter()
                    vector = extractors[m].extract(img)
                    elapsed[m] += time.perf_counter() - t0
                    writers[m].writerow([rel_path, cls] + vector.tolist())
                total += 1
                if total % 50 == 0:
                    print(f"  {total} images traitées...")
            except Exception as e:
                print(f"  ERREUR {rel_path}: {e}")
    finally:
        for f in files.values():
            f.close()

    stats = load_extraction_stats()
    for m in models:
        if total:
            stats[m] = {"mean_extract_ms": elapsed[m] / total * 1000}
        print(f"\n{MODELS[m]['label']} — {total} vecteurs → {MODELS[m]['features_csv']}")
        if total:
            print(f"  temps moyen d'extraction : {stats[m]['mean_extract_ms']:.1f} ms/image")
    save_extraction_stats(stats)


if __name__ == "__main__":
    main()
