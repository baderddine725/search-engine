"""
Génère data/photo_metadata.csv depuis la base d'images locale (bdimage/<classe>/).

Flickr-style : chaque image reçoit un title et des tags dérivés de sa classe,
pour que la recherche textuelle fonctionne même sans l'archive MIRFLICKR
(celle-ci reste la source de vérité pour la base 1M).
"""

import csv
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))

from config import BDIMAGE_DIR, CSV_PATH, ALLOWED_EXTENSIONS

# Tags supplémentaires par classe pour enrichir le vocabulaire indexé
EXTRA_TAGS = {
    "daisy":      ["daisy", "flower", "white", "yellow", "petals", "spring", "garden"],
    "dandelion":  ["dandelion", "flower", "yellow", "weed", "seeds", "spring", "field"],
    "roses":      ["rose", "flower", "red", "pink", "garden", "petals", "bloom", "love"],
    "sunflowers": ["sunflower", "flower", "yellow", "sun", "summer", "big", "field"],
    "tulips":     ["tulip", "flower", "spring", "garden", "colorful", "petals", "bulb"],
}


def main():
    rows = []
    for cls in sorted(os.listdir(BDIMAGE_DIR)):
        folder = os.path.join(BDIMAGE_DIR, cls)
        if not os.path.isdir(folder):
            continue
        for fn in sorted(os.listdir(folder)):
            if fn.rsplit(".", 1)[-1].lower() not in ALLOWED_EXTENSIONS:
                continue
            # Flickr-style photo_id = stem numérique du fichier quand il existe
            stem = fn.rsplit(".", 1)[0]
            tags = EXTRA_TAGS.get(cls, [cls])
            rows.append({
                "photo_id": stem,
                "title": f"{cls.rstrip('s').capitalize()} photo",
                "tags": " ".join(tags),
                "description": f"A photograph of a {cls.rstrip('s')}.",
                "farm": 1,
                "server": "0",
                "secret": stem,
                "image_path": f"{cls}/{fn}",   # chemin interne (base locale)
            })

    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    cols = ["photo_id", "title", "tags", "description",
            "farm", "server", "secret", "image_path"]
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Écrit {len(rows)} lignes → {CSV_PATH}")


if __name__ == "__main__":
    main()
