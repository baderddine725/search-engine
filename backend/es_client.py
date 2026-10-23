"""Client Elasticsearch — recherche textuelle et recherche par image."""

from typing import Optional

from elasticsearch import Elasticsearch
import numpy as np

from config import (
    ES_URL,
    TEXT_INDEX,
    MODELS,
    DEFAULT_MODEL,
    ANN_CANDIDATES,
    DEFAULT_RESULTS,
)


def get_es() -> Elasticsearch:
    """Retourne une connexion Elasticsearch."""
    return Elasticsearch(ES_URL)


# ======================================================================
# Création des index
# ======================================================================

TEXT_MAPPING = {
    "mappings": {
        "properties": {
            "photo_id": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "standard"},
            "tags": {"type": "text", "analyzer": "standard"},
            "description": {"type": "text", "analyzer": "standard"},
            "farm": {"type": "integer"},
            "server": {"type": "keyword"},
            "secret": {"type": "keyword"},
            "url": {"type": "keyword"},
        }
    }
}

DEFAULT_LSH = {"L": 99, "k": 1, "w": 3}


def image_mapping(model: str) -> dict:
    """Mapping Elastiknn (L2 LSH) pour l'index d'un modèle."""
    cfg = MODELS[model]
    return {
        "settings": {
            "elastiknn": True,
        },
        "mappings": {
            "properties": {
                "image_path": {"type": "keyword"},
                "class_name": {"type": "keyword"},
                "vector": {
                    "type": "elastiknn_dense_float_vector",
                    "elastiknn": {
                        "dims": cfg["dims"],
                        "similarity": "l2",
                        "model": "lsh",
                        **cfg.get("lsh", DEFAULT_LSH),
                    },
                },
            }
        },
    }


def create_indices(es: Elasticsearch, models=None):
    """Crée l'index texte et les index image s'ils n'existent pas."""
    if not es.indices.exists(index=TEXT_INDEX):
        es.indices.create(index=TEXT_INDEX, body=TEXT_MAPPING)
        print(f"Index '{TEXT_INDEX}' créé.")
    for model in models or MODELS:
        index = MODELS[model]["index"]
        if not es.indices.exists(index=index):
            es.indices.create(index=index, body=image_mapping(model))
            print(f"Index '{index}' créé.")


def recreate_image_index(es: Elasticsearch, model: str):
    """Supprime puis recrée l'index image d'un modèle (réindexation propre)."""
    index = MODELS[model]["index"]
    es.indices.delete(index=index, ignore=[404])
    es.indices.create(index=index, body=image_mapping(model))


def count(es: Elasticsearch, index: str) -> int:
    if not es.indices.exists(index=index):
        return 0
    return es.count(index=index)["count"]


# ======================================================================
# Recherche textuelle (TBIR)
# ======================================================================

def flickr_url(src: dict) -> str:
    """URL Flickr (format live.staticflickr.com, toujours servi)."""
    if src.get("server") and src.get("photo_id") and src.get("secret"):
        return (
            f"https://live.staticflickr.com/"
            f"{src['server']}/{src['photo_id']}_{src['secret']}.jpg"
        )
    return src.get("url", "")


def search_text(es: Elasticsearch, query: str, size: int = DEFAULT_RESULTS) -> list:
    """
    Recherche multi-champ avec fuzzy et boosting.
    Retourne une liste de résultats avec score et métadonnées.
    """
    body = {
        "size": size,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title^3", "tags^2", "description"],
                "fuzziness": "AUTO",
            }
        },
        "highlight": {
            "fields": {"title": {}, "tags": {}, "description": {}},
            "pre_tags": ["**"],
            "post_tags": ["**"],
        },
    }
    resp = es.search(index=TEXT_INDEX, body=body)
    results = []
    for hit in resp["hits"]["hits"]:
        src = hit["_source"]
        results.append({
            "photo_id": src.get("photo_id"),
            "title": src.get("title", ""),
            "tags": src.get("tags", ""),
            "description": src.get("description", ""),
            "url": flickr_url(src),
            "score": hit["_score"],
            "highlight": hit.get("highlight", {}),
        })
    return results


# ======================================================================
# Recherche par image (CBIR)
# ======================================================================

def _knn_query(vec: dict, candidates: int, exact: bool = False) -> dict:
    if exact:
        # Recherche exhaustive (référence sans approximation)
        return {
            "elastiknn_nearest_neighbors": {
                "field": "vector", "vec": vec, "similarity": "l2", "model": "exact",
            }
        }
    return {
        "elastiknn_nearest_neighbors": {
            "field": "vector",
            "vec": vec,
            "similarity": "l2",
            "model": "lsh",
            "candidates": candidates,
            # Requis par Elastiknn 7.17.x pour L2 LSH (0 = LSH standard, sans multiprobe)
            "probes": 0,
        }
    }


def _image_hits(resp: dict, exclude: Optional[str], size: int) -> list:
    results = []
    for hit in resp["hits"]["hits"]:
        src = hit["_source"]
        if exclude and src.get("image_path") == exclude:
            continue
        score = hit["_score"]
        results.append({
            "image_path": src.get("image_path", ""),
            "class_name": src.get("class_name", ""),
            "score": score,
            # Elastiknn L2 : score = 1 / (1 + distance)
            "distance": (1.0 / score - 1.0) if score else None,
        })
    return results[:size]


def search_image(
    es: Elasticsearch,
    vector: np.ndarray,
    size: int = DEFAULT_RESULTS,
    candidates: int = ANN_CANDIDATES,
    model: str = DEFAULT_MODEL,
) -> list:
    """
    Recherche ANN via Elastiknn (L2 LSH).
    Retourne les images les plus similaires.
    """
    body = {
        "size": size,
        "_source": ["image_path", "class_name"],
        "query": _knn_query({"values": vector.tolist()}, max(candidates, size)),
    }
    resp = es.search(index=MODELS[model]["index"], body=body)
    return _image_hits(resp, None, size)


def search_similar_indexed(
    es: Elasticsearch,
    image_path: str,
    size: int = DEFAULT_RESULTS,
    candidates: int = ANN_CANDIDATES,
    model: str = DEFAULT_MODEL,
    exact: bool = False,
) -> list:
    """Recherche à partir d'une image déjà indexée (l'image elle-même est exclue)."""
    index = MODELS[model]["index"]
    body = {
        "size": size + 1,
        "_source": ["image_path", "class_name"],
        "query": _knn_query(
            {"index": index, "id": image_path, "field": "vector"},
            max(candidates, size + 1),
            exact,
        ),
    }
    resp = es.search(index=index, body=body)
    return _image_hits(resp, image_path, size)


# ======================================================================
# Exploration de la base d'images
# ======================================================================

def class_counts(es: Elasticsearch, model: str = DEFAULT_MODEL) -> dict:
    """Nombre d'images indexées par classe."""
    index = MODELS[model]["index"]
    if not es.indices.exists(index=index):
        return {}
    body = {
        "size": 0,
        "aggs": {"classes": {"terms": {"field": "class_name", "size": 1000}}},
    }
    resp = es.search(index=index, body=body)
    return {
        b["key"]: b["doc_count"]
        for b in resp["aggregations"]["classes"]["buckets"]
    }


def list_images(
    es: Elasticsearch,
    class_name: Optional[str] = None,
    size: int = 20,
    random: bool = False,
    seed: Optional[int] = None,
    model: str = DEFAULT_MODEL,
) -> list:
    """Liste des images indexées (optionnellement filtrées par classe / aléatoires)."""
    query = {"term": {"class_name": class_name}} if class_name else {"match_all": {}}
    if random:
        random_score = {"seed": seed, "field": "_seq_no"} if seed is not None else {}
        query = {"function_score": {"query": query, "random_score": random_score}}
    body = {"size": size, "_source": ["image_path", "class_name"], "query": query}
    if not random:
        body["sort"] = [{"image_path": "asc"}]
    resp = es.search(index=MODELS[model]["index"], body=body)
    return [h["_source"] for h in resp["hits"]["hits"]]
