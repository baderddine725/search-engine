"""Évaluation comparative des modèles CBIR (précision, mAP, temps de réponse).

Protocole : chaque image indexée (ou un échantillon par classe) sert de requête ;
elle est exclue de ses propres résultats ; un résultat est pertinent s'il
appartient à la même classe que la requête.
"""

import json
import os
import random
import time
from datetime import datetime, timezone
from typing import Optional

from elasticsearch import Elasticsearch

from config import MODELS, ANN_CANDIDATES, BENCHMARK_JSON, EXTRACTION_STATS_JSON
from es_client import class_counts, list_images, search_similar_indexed


def query_metrics(results: list, query_class: str, class_size: Optional[int], k: int) -> dict:
    """Précision@k et AP@k pour une liste de résultats ordonnés.

    class_size : nombre d'images pertinentes disponibles (requête exclue).
    """
    rel = [r["class_name"] == query_class for r in results[:k]]
    hits, ap_sum, curve = 0, 0.0, []
    for i, is_rel in enumerate(rel, start=1):
        if is_rel:
            hits += 1
            ap_sum += hits / i
        curve.append(hits / i)
    n_relevant = min(k, class_size) if class_size else hits
    return {
        "precision": hits / k if k else 0.0,
        "ap": ap_sum / n_relevant if n_relevant else 0.0,
        "relevant": hits,
        "curve": curve,
    }


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _sample_queries(es: Elasticsearch, counts: dict, per_class: Optional[int], seed: int) -> list:
    rng = random.Random(seed)
    queries = []
    for cls in sorted(counts):
        images = list_images(es, class_name=cls, size=counts[cls])
        if per_class and per_class < len(images):
            images = rng.sample(images, per_class)
        queries.extend(images)
    return queries


def _index_size_mb(es: Elasticsearch, index: str) -> float:
    stats = es.indices.stats(index=index, metric="store")
    return stats["_all"]["primaries"]["store"]["size_in_bytes"] / 1e6


def _evaluate_mode(es, model, queries, model_counts, k, candidates, exact) -> dict:
    """Métriques agrégées d'un modèle, en recherche approchée (LSH) ou exacte."""
    per_query = []
    for q in queries:
        t0 = time.perf_counter()
        results = search_similar_indexed(
            es, q["image_path"], size=k, candidates=candidates, model=model, exact=exact
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        m = query_metrics(results, q["class_name"], model_counts.get(q["class_name"], 1) - 1, k)
        m.update(class_name=q["class_name"], ms=elapsed_ms)
        per_query.append(m)

    per_class = {}
    for cls in sorted({q["class_name"] for q in queries}):
        rows = [m for m in per_query if m["class_name"] == cls]
        per_class[cls] = {
            "precision": _mean(m["precision"] for m in rows),
            "ap": _mean(m["ap"] for m in rows),
            "n": len(rows),
        }
    return {
        "precision": _mean(m["precision"] for m in per_query),
        "map": _mean(m["ap"] for m in per_query),
        "p_at_1": _mean(m["curve"][0] for m in per_query if m["curve"]),
        "precision_curve": [
            _mean(m["curve"][i] for m in per_query if len(m["curve"]) > i)
            for i in range(k)
        ],
        "mean_query_ms": _mean(m["ms"] for m in per_query),
        "per_class": per_class,
    }


def run_benchmark(
    es: Elasticsearch,
    k: int = 10,
    per_class: Optional[int] = 20,
    candidates: int = ANN_CANDIDATES,
    seed: int = 42,
    extraction_stats: Optional[dict] = None,
) -> dict:
    """Évalue tous les modèles sur les mêmes requêtes (LSH et exact) et retourne un rapport."""
    counts = class_counts(es)  # référence : index de notre approche
    if not counts:
        raise RuntimeError("Aucune image indexée — lancez extract_features.py puis index_images.py.")
    queries = _sample_queries(es, counts, per_class, seed)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "k": k,
        "candidates": candidates,
        "n_queries": len(queries),
        "n_images": sum(counts.values()),
        "classes": counts,
        "models": {},
    }
    for model, cfg in MODELS.items():
        model_counts = class_counts(es, model)
        if not model_counts:
            continue
        lsh = _evaluate_mode(es, model, queries, model_counts, k, candidates, exact=False)
        exact = _evaluate_mode(es, model, queries, model_counts, k, candidates, exact=True)
        report["models"][model] = {
            "label": cfg["label"],
            "dims": cfg["dims"],
            **lsh,
            "exact": exact,
            "index_size_mb": _index_size_mb(es, cfg["index"]),
            **((extraction_stats or {}).get(model, {})),
        }
    return report


def save_report(report: dict, path: str = BENCHMARK_JSON):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def load_report(path: str = BENCHMARK_JSON) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_extraction_stats(path: str = EXTRACTION_STATS_JSON) -> dict:
    """Temps moyen d'extraction par modèle (écrit par extract_features.py)."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_extraction_stats(stats: dict, path: str = EXTRACTION_STATS_JSON):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
