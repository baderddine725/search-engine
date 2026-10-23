"""API Flask — moteur de recherche texte + image, comparaison InceptionV3+LBP / VGG16."""

import os
import time

from flask import Flask, request, jsonify, send_from_directory
from PIL import Image
from elasticsearch import NotFoundError

from config import (
    MAX_CONTENT_LENGTH,
    ALLOWED_EXTENSIONS,
    BDIMAGE_DIR,
    DEFAULT_RESULTS,
    DEFAULT_MODEL,
    ANN_CANDIDATES,
    MODELS,
    TEXT_INDEX,
)
from es_client import (
    get_es,
    search_text,
    search_image,
    search_similar_indexed,
    create_indices,
    class_counts,
    list_images,
    count,
)
from evaluation import (
    query_metrics,
    run_benchmark,
    save_report,
    load_report,
    load_extraction_stats,
)
from feature_extractor import (
    get_extractor,
    load_image_from_bytes,
    load_image_from_url,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Initialisation globale : chargement + préchauffage des modèles (le premier
# appel TensorFlow est lent), pour que la première requête soit rapide.
es = get_es()
for _model in MODELS:
    get_extractor(_model).extract(Image.new("RGB", (64, 64)))

MAX_RESULTS = 100


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


@app.errorhandler(ApiError)
def handle_api_error(e: ApiError):
    return jsonify({"error": e.message}), e.status


@app.errorhandler(NotFoundError)
def handle_es_not_found(e):
    return jsonify({"error": "Index ou document introuvable. Avez-vous indexé les données ?"}), 404


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ------------------------------------------------------------------
# Lecture des paramètres
# ------------------------------------------------------------------

def _params() -> dict:
    """Fusionne query string, formulaire et corps JSON."""
    params = dict(request.args)
    params.update(request.form.to_dict())
    params.update(request.get_json(silent=True) or {})
    return params


def _int_param(params: dict, name: str, default: int, lo: int = 1, hi: int = MAX_RESULTS) -> int:
    try:
        value = int(params.get(name, default))
    except (TypeError, ValueError):
        raise ApiError(f"Le paramètre '{name}' doit être un entier.")
    return max(lo, min(hi, value))


def _model_param(params: dict) -> str:
    model = params.get("model", DEFAULT_MODEL)
    if model not in MODELS:
        raise ApiError(f"Modèle inconnu '{model}'. Choix : {', '.join(MODELS)}.")
    return model


def _query_image(params: dict):
    """Image requête depuis un upload ('image') ou une URL ('url')."""
    if "image" in request.files:
        file = request.files["image"]
        if file.filename == "":
            raise ApiError("Nom de fichier vide.")
        if not allowed_file(file.filename):
            raise ApiError("Extension non autorisée.")
        try:
            return load_image_from_bytes(file.read())
        except Exception:
            raise ApiError("Fichier image illisible.")
    url = (params.get("url") or "").strip()
    if url:
        try:
            return load_image_from_url(url)
        except Exception as e:
            raise ApiError(f"Impossible de télécharger l'image : {e}")
    raise ApiError("Fournissez une image ('image') ou une URL ('url').")


def _search_with_image(img, model: str, size: int, candidates: int) -> dict:
    t0 = time.perf_counter()
    vector = get_extractor(model).extract(img)
    t1 = time.perf_counter()
    results = search_image(es, vector, size=size, candidates=candidates, model=model)
    t2 = time.perf_counter()
    return {
        "results": results,
        "extract_ms": (t1 - t0) * 1000,
        "search_ms": (t2 - t1) * 1000,
    }


def _search_with_path(path: str, model: str, size: int, candidates: int) -> dict:
    t0 = time.perf_counter()
    results = search_similar_indexed(es, path, size=size, candidates=candidates, model=model)
    return {
        "results": results,
        "extract_ms": 0.0,  # vecteur déjà indexé
        "search_ms": (time.perf_counter() - t0) * 1000,
    }


def _class_of(path: str) -> str:
    """bdimage/<classe>/<fichier> → classe."""
    parts = path.replace("\\", "/").split("/")
    return parts[0] if len(parts) > 1 else ""


# ------------------------------------------------------------------
# Routes — service
# ------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Vérification de santé du service."""
    try:
        info = es.info()
        return jsonify({
            "status": "ok",
            "elasticsearch": info["version"]["number"],
        })
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 503


@app.route("/models", methods=["GET"])
def models():
    return jsonify({
        "default": DEFAULT_MODEL,
        "models": {
            name: {k: cfg[k] for k in ("label", "description", "dims", "index")}
            for name, cfg in MODELS.items()
        },
    })


@app.route("/stats", methods=["GET"])
def stats():
    """Volumétrie des index et répartition des classes."""
    return jsonify({
        "text_documents": count(es, TEXT_INDEX),
        "models": {
            name: {"label": cfg["label"], "images": count(es, cfg["index"])}
            for name, cfg in MODELS.items()
        },
        "classes": class_counts(es),
        "benchmark_available": load_report() is not None,
    })


@app.route("/init", methods=["POST"])
def init_indices():
    """Crée les index Elasticsearch (utile au premier lancement)."""
    try:
        create_indices(es)
        return jsonify({"status": "ok", "message": "Index initialisés."})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500


# ------------------------------------------------------------------
# Routes — recherche
# ------------------------------------------------------------------

@app.route("/search/text", methods=["GET"])
def text_search():
    """
    Recherche textuelle (TBIR).
    Params: q (query), size (nombre de résultats).
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Le paramètre 'q' est requis."}), 400

    size = _int_param(request.args, "size", DEFAULT_RESULTS)
    t0 = time.perf_counter()
    results = search_text(es, query, size=size)
    return jsonify({
        "query": query,
        "count": len(results),
        "results": results,
        "search_ms": (time.perf_counter() - t0) * 1000,
    })


@app.route("/search/image", methods=["POST"])
def image_search():
    """
    Recherche par image uploadée (CBIR).
    Multipart form : champ 'image', optionnels 'size', 'model'.
    """
    params = _params()
    if "image" not in request.files:
        raise ApiError("Aucun fichier 'image' envoyé.")
    model = _model_param(params)
    size = _int_param(params, "size", DEFAULT_RESULTS)
    out = _search_with_image(_query_image(params), model, size, ANN_CANDIDATES)
    return jsonify({"model": model, "count": len(out["results"]), **out})


@app.route("/search/url", methods=["POST"])
def url_search():
    """
    Recherche par URL d'image (CBIR).
    JSON body : { "url": "...", "size": 10, "model": "inception_lbp" }
    """
    params = _params()
    if not (params.get("url") or "").strip():
        raise ApiError("Le champ 'url' est requis.")
    model = _model_param(params)
    size = _int_param(params, "size", DEFAULT_RESULTS)
    out = _search_with_image(_query_image(params), model, size, ANN_CANDIDATES)
    return jsonify({"url": params["url"], "model": model, "count": len(out["results"]), **out})


@app.route("/search/similar", methods=["GET"])
def similar_search():
    """Recherche à partir d'une image de la base. Params : path, size, model."""
    path = request.args.get("path", "").strip()
    if not path:
        raise ApiError("Le paramètre 'path' est requis.")
    model = _model_param(request.args)
    size = _int_param(request.args, "size", DEFAULT_RESULTS)
    out = _search_with_path(path, model, size, ANN_CANDIDATES)
    return jsonify({"path": path, "model": model, "count": len(out["results"]), **out})


# ------------------------------------------------------------------
# Routes — comparaison InceptionV3+LBP vs VGG16
# ------------------------------------------------------------------

@app.route("/compare", methods=["POST"])
def compare():
    """
    Lance la même requête sur tous les modèles.
    Requête : 'image' (upload), 'url', ou 'path' (image de la base).
    Optionnels : 'size', 'candidates', 'query_class' (classe attendue → métriques).
    """
    params = _params()
    size = _int_param(params, "size", DEFAULT_RESULTS)
    candidates = _int_param(params, "candidates", ANN_CANDIDATES, hi=1000)
    path = (params.get("path") or "").strip()

    if path:
        query_class = _class_of(path)
        run = lambda m: _search_with_path(path, m, size, candidates)
    else:
        img = _query_image(params)
        query_class = (params.get("query_class") or "").strip()
        run = lambda m: _search_with_image(img, m, size, candidates)

    out = {}
    for model, cfg in MODELS.items():
        res = run(model)
        res["label"] = cfg["label"]
        if query_class:
            n_class = class_counts(es, model).get(query_class, 0)
            res["metrics"] = query_metrics(
                res["results"], query_class, n_class - 1 if path else n_class, size
            )
        out[model] = res

    names = list(out)
    sets = [{r["image_path"] for r in out[m]["results"]} for m in names]
    overlap = set.intersection(*sets) if sets else set()
    return jsonify({
        "query_class": query_class or None,
        "size": size,
        "models": out,
        "overlap": sorted(overlap),
    })


@app.route("/benchmark", methods=["GET"])
def benchmark():
    """Dernier rapport d'évaluation calculé."""
    report = load_report()
    if report is None:
        raise ApiError("Aucun rapport. Lancez POST /benchmark/run ou scripts/evaluate.py.", 404)
    return jsonify(report)


@app.route("/benchmark/run", methods=["POST"])
def benchmark_run():
    """Recalcule le rapport. Params : k, per_class (0 = toutes les images), candidates."""
    params = _params()
    k = _int_param(params, "k", 10, hi=50)
    per_class = _int_param(params, "per_class", 20, lo=0, hi=100000) or None
    candidates = _int_param(params, "candidates", ANN_CANDIDATES, hi=1000)
    try:
        report = run_benchmark(
            es, k=k, per_class=per_class, candidates=candidates,
            extraction_stats=load_extraction_stats(),
        )
    except RuntimeError as e:
        raise ApiError(str(e), 409)
    save_report(report)
    return jsonify(report)


# ------------------------------------------------------------------
# Routes — base d'images
# ------------------------------------------------------------------

@app.route("/dataset/images", methods=["GET"])
def dataset_images():
    """Liste d'images indexées. Params : class, size, random (0/1), seed."""
    size = _int_param(request.args, "size", 20, hi=500)
    seed = request.args.get("seed", type=int)
    images = list_images(
        es,
        class_name=request.args.get("class") or None,
        size=size,
        random=request.args.get("random", "0") == "1",
        seed=seed,
    )
    return jsonify({"count": len(images), "images": images})


@app.route("/images/<path:filepath>", methods=["GET"])
def serve_image(filepath):
    """Sert les images locales de la base bdimage."""
    return send_from_directory(BDIMAGE_DIR, filepath, max_age=86400)


# ------------------------------------------------------------------
# Point d'entrée
# ------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
