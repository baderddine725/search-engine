"""
Évaluation comparative InceptionV3+LBP vs VGG16 sur la base indexée.
Écrit data/benchmark.json (affiché dans l'onglet « Comparaison » du frontend).

Usage : python evaluate.py [--k 10] [--per-class 0]   (0 = toutes les images)
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from config import ANN_CANDIDATES, BENCHMARK_JSON
from es_client import get_es
from evaluation import run_benchmark, save_report, load_extraction_stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--per-class", type=int, default=0)
    parser.add_argument("--candidates", type=int, default=ANN_CANDIDATES)
    args = parser.parse_args()

    report = run_benchmark(
        get_es(),
        k=args.k,
        per_class=args.per_class or None,
        candidates=args.candidates,
        extraction_stats=load_extraction_stats(),
    )
    save_report(report)

    print(f"{report['n_queries']} requêtes, k={report['k']}\n")
    print(f"{'Modèle':<20}{'Recherche':<10}{'P@k':>8}{'mAP':>8}{'P@1':>8}{'ms/req':>9}")
    for m in report["models"].values():
        for mode, r in (("LSH", m), ("exacte", m["exact"])):
            print(
                f"{m['label']:<20}{mode:<10}{r['precision']:>8.3f}{r['map']:>8.3f}"
                f"{r['p_at_1']:>8.3f}{r['mean_query_ms']:>9.1f}"
            )
        if m.get("mean_extract_ms"):
            print(f"{'':<20}extraction : {m['mean_extract_ms']:.1f} ms/image")
    print(f"\nRapport → {BENCHMARK_JSON}")


if __name__ == "__main__":
    main()
