"""
Indexation des métadonnées textuelles Flickr dans Elasticsearch.
Lit le CSV photo_metadata.csv et bulk-indexe dans l'index 'flickrphotos'.
"""

import os
import sys
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from elasticsearch import helpers
from config import CSV_PATH, TEXT_INDEX
from es_client import get_es, create_indices


def generate_docs(csv_path: str):
    """Génère les documents à indexer depuis le CSV."""
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            photo_id = row.get("photo_id", row.get("id", ""))
            farm = row.get("farm", 0)
            server = row.get("server", "")
            secret = row.get("secret", "")

            url = (
                f"http://farm{farm}.staticflickr.com/"
                f"{server}/{photo_id}_{secret}.jpg"
            )

            yield {
                "_index": TEXT_INDEX,
                "_id": photo_id,
                "_source": {
                    "photo_id": photo_id,
                    "title": row.get("title", ""),
                    "tags": row.get("tags", ""),
                    "description": row.get("description", ""),
                    "farm": int(farm) if farm else 0,
                    "server": server,
                    "secret": secret,
                    "url": url,
                },
            }


def main():
    es = get_es()
    create_indices(es)

    print(f"Indexation du fichier : {CSV_PATH}")
    if not os.path.exists(CSV_PATH):
        print(f"ERREUR : fichier introuvable → {CSV_PATH}")
        sys.exit(1)

    success, errors = helpers.bulk(es, generate_docs(CSV_PATH), chunk_size=1000)
    print(f"Indexation terminée — {success} documents indexés, {len(errors)} erreurs.")


if __name__ == "__main__":
    main()
