"""
Indexation des vecteurs de features dans Elasticsearch (un index par modèle).
Lit les CSV produits par extract_features.py. L'index est recréé à chaque
exécution pour éviter les doublons.

Usage : python index_images.py [--model all|inception_lbp|vgg16]
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from elasticsearch import helpers
from config import MODELS
from es_client import get_es, create_indices, recreate_image_index

csv.field_size_limit(10 ** 8)


def generate_docs(csv_path: str, index: str, dims: int):
    """Génère les documents vectoriels à indexer."""
    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        next(reader)  # Sauter l'en-tête

        for row in reader:
            image_path = row[0].replace("\\", "/")
            yield {
                "_index": index,
                "_id": image_path,
                "_source": {
                    "image_path": image_path,
                    "class_name": row[1],
                    "vector": {"values": [float(v) for v in row[2 : 2 + dims]]},
                },
            }


def index_model(es, model: str):
    cfg = MODELS[model]
    print(f"[{cfg['label']}] indexation de {cfg['features_csv']} → {cfg['index']}")
    if not os.path.exists(cfg["features_csv"]):
        print(f"  ERREUR : fichier introuvable → {cfg['features_csv']}")
        print("  Lancez d'abord : python extract_features.py")
        return False
    recreate_image_index(es, model)
    success, errors = helpers.bulk(
        es, generate_docs(cfg["features_csv"], cfg["index"], cfg["dims"]),
        chunk_size=200, request_timeout=120,
    )
    es.indices.refresh(index=cfg["index"])
    print(f"  {success} vecteurs indexés, {len(errors)} erreurs.")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="all", choices=["all", *MODELS])
    args = parser.parse_args()

    es = get_es()
    create_indices(es)
    models = list(MODELS) if args.model == "all" else [args.model]
    ok = all([index_model(es, m) for m in models])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
