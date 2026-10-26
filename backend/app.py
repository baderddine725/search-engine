"""API Flask — moteur de recherche texte + image, comparaison InceptionV3+LBP / VGG16."""

import math
import os
import time

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
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
# CORS ouvert : le frontend web (VisionSearch AI) tourne sur un autre port.
CORS(app, resources={r"/*": {"origins": "*"}})

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


# ------------------------------------------------------------------
# Routes — descripteurs classiques (color / lbp / hog) + VP-Tree
# ------------------------------------------------------------------

@app.route("/descriptors", methods=["GET"])
def descriptors_list():
    """Descripteurs classiques disponibles (ceux dont l'index VP-Tree existe)."""
    from descriptors import DESCRIPTORS
    from descriptor_index import available
    avail = available()
    return jsonify({
        "available": avail,
        "descriptors": {
            name: DESCRIPTORS[name] for name in avail
        },
        "all": DESCRIPTORS,
    })


def _descriptors_param(params: dict) -> tuple:
    from descriptors import DESCRIPTORS
    raw = params.get("descriptors", "")
    if isinstance(raw, list):
        names = [str(x).strip() for x in raw if str(x).strip()]
    else:
        names = [x.strip() for x in str(raw).split(",") if x.strip()]
    if not names:
        raise ApiError("Paramètre 'descriptors' requis (ex: color,lbp,hog).")
    for n in names:
        if n not in DESCRIPTORS:
            raise ApiError(f"Descripteur inconnu : {n}")
    weights_raw = params.get("weights", "")
    try:
        if isinstance(weights_raw, list):
            weights = [float(w) for w in weights_raw]
        elif str(weights_raw).strip():
            weights = [float(w) for w in str(weights_raw).split(",")]
        else:
            weights = [1.0] * len(names)
    except (TypeError, ValueError):
        raise ApiError("'weights' doit être une liste de nombres (ex: 1,0.5).")
    if len(weights) != len(names):
        raise ApiError("'weights' doit avoir la même longueur que 'descriptors'.")
    if not all(math.isfinite(w) and w >= 0 for w in weights) or sum(weights) <= 0:
        raise ApiError("'weights' doit contenir des nombres positifs, de somme non nulle.")
    return names, weights


@app.route("/search/descriptor", methods=["POST"])
def descriptor_search():
    """
    Recherche k-NN par descripteurs classiques via VP-Tree.
    Query : 'image' (upload) OU 'url' OU 'path' (image de la base).
    Params : descriptors (ex. 'color,lbp'), weights (ex. '1,0.5'), size, exact.
    """
    from descriptor_index import search as desc_search
    params = _params()
    size = _int_param(params, "size", DEFAULT_RESULTS)
    exact = str(params.get("exact", "0")).lower() in ("1", "true", "yes")
    names, weights = _descriptors_param(params)
    path = (params.get("path") or "").strip()
    kwargs = {"descriptors": names, "weights": weights, "k": size, "exact": exact}
    if path:
        kwargs["image_path"] = path
    else:
        kwargs["image"] = _query_image(params)
    out = desc_search(**kwargs)
    return jsonify({"descriptors": names, "weights": weights, "exact": exact,
                    "count": len(out["results"]), **out})


@app.route("/search/combined", methods=["POST"])
def combined_search():
    """
    Requête mixte texte + image :
      - texte  (`q`)         : facultatif → filtre et pondère sur l'index flickrphotos
      - visuel ('path' | 'image' | 'url') : facultatif, descripteurs choisis
    Au moins l'un des deux est requis.
    """
    from descriptor_index import search as desc_search
    params = _params()
    size = _int_param(params, "size", DEFAULT_RESULTS)
    q = (params.get("q") or "").strip()
    path = (params.get("path") or "").strip()
    has_image = bool(path) or "image" in request.files or (params.get("url") or "").strip()

    if not q and not has_image:
        raise ApiError("Fournissez 'q' et/ou une image/'path'.")

    out = {"query": q or None, "size": size}
    text_hits = []
    if q:
        t0 = time.perf_counter()
        text_hits = search_text(es, q, size=max(size * 5, 50))
        out["text_ms"] = (time.perf_counter() - t0) * 1000

    img_results = []
    if has_image:
        names, weights = _descriptors_param(params)
        exact = str(params.get("exact", "0")).lower() in ("1", "true", "yes")
        kwargs = {"descriptors": names, "weights": weights,
                  "k": max(size * 5, 50), "exact": exact}
        if path:
            kwargs["image_path"] = path
        else:
            kwargs["image"] = _query_image(params)
        vis = desc_search(**kwargs)
        img_results = vis["results"]
        out.update({"descriptors": names, "weights": weights,
                    "extract_ms": vis.get("extract_ms"),
                    "visual_ms": vis.get("search_ms")})

    # Fusion : rank-based (reciprocal rank fusion), robuste à la différence
    # d'échelles entre score BM25 et distance L1.
    K_RRF = 60
    rrf: dict = {}
    text_path = {r.get("image_path"): r for r in text_hits if r.get("image_path")}
    for rank, r in enumerate(text_hits):
        p = r.get("image_path")
        if not p:
            continue
        rrf[p] = rrf.get(p, 0.0) + 1.0 / (K_RRF + rank + 1)
    for rank, r in enumerate(img_results):
        p = r.get("image_path")
        rrf[p] = rrf.get(p, 0.0) + 1.0 / (K_RRF + rank + 1)
    img_by_path = {r["image_path"]: r for r in img_results}
    merged = sorted(rrf.items(), key=lambda kv: -kv[1])[:size]
    results = []
    for p, score in merged:
        tr = text_path.get(p, {})
        vr = img_by_path.get(p, {})
        results.append({
            "image_path": p,
            "class_name": vr.get("class_name") or _class_of(p),
            "rrf_score": score,
            "text_score": tr.get("score"),
            "visual_distance": vr.get("distance"),
            "title": tr.get("title"),
            "tags": tr.get("tags"),
            "url": tr.get("url"),
        })
    out["count"] = len(results)
    out["results"] = results
    return jsonify(out)


# ------------------------------------------------------------------
# Routes — MIRFLICKR-1M (texte Flickr + MPEG-7)
# ------------------------------------------------------------------

MIRFLICKR_INDEX = "mirflickr"


@app.route("/mirflickr/thumb/<int:photo_id>", methods=["GET"])
def mirflickr_thumb(photo_id):
    """Serve the MIRFLICKR thumbnail JPEG for a given photo id."""
    from flask import Response, abort
    from mirflickr_thumbs import thumb
    try:
        data = thumb(photo_id)
    except FileNotFoundError:
        abort(404)
    resp = Response(data, mimetype="image/jpeg")
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


@app.route("/mirflickr/stats", methods=["GET"])
def mirflickr_stats():
    """État de l'index MIRFLICKR-1M."""
    try:
        from mirflickr_index import available
        descriptors = available()
    except Exception:
        descriptors = []
    try:
        from mirflickr_thumbs import available as thumbs_available
        thumbs = thumbs_available()
    except Exception:
        thumbs = {}
    docs = count(es, MIRFLICKR_INDEX)
    return jsonify({
        "indexed_documents": docs,
        "mpeg7_descriptors": descriptors,
        "has_text": docs > 0,
        "thumbs": thumbs,
    })


@app.route("/mirflickr/search", methods=["GET"])
def mirflickr_text_search():
    """Recherche textuelle BM25 dans la base MIRFLICKR-1M."""
    q = (request.args.get("q") or "").strip()
    if not q:
        raise ApiError("Le paramètre 'q' est requis.")
    size = _int_param(request.args, "size", DEFAULT_RESULTS)
    t0 = time.perf_counter()
    body = {
        "size": size,
        "query": {"multi_match": {
            "query": q, "fields": ["title^2", "tags"], "fuzziness": "AUTO",
        }},
        "highlight": {"fields": {"title": {}, "tags": {}},
                      "pre_tags": ["**"], "post_tags": ["**"]},
    }
    resp = es.search(index=MIRFLICKR_INDEX, body=body)
    results = [{
        "photo_id": h["_source"].get("photo_id"),
        "title": h["_source"].get("title", ""),
        "tags": h["_source"].get("tags", ""),
        "owner": h["_source"].get("owner", ""),
        "license": h["_source"].get("license", ""),
        "url": h["_source"].get("url", ""),
        "score": h["_score"],
        "highlight": h.get("highlight", {}),
    } for h in resp["hits"]["hits"]]
    return jsonify({
        "query": q, "count": len(results),
        "total": resp["hits"]["total"]["value"],
        "results": results,
        "search_ms": (time.perf_counter() - t0) * 1000,
    })


def _mirflickr_query_image():
    """Load the query image for the MIRFLICKR search routes (upload or URL)."""
    params = _params()
    if "image" in request.files:
        file = request.files["image"]
        if file.filename == "":
            raise ApiError("Fichier vide.")
        if not allowed_file(file.filename):
            raise ApiError("Extension non autorisée.")
        try:
            return load_image_from_bytes(file.read()), None
        except Exception:
            raise ApiError("Image illisible.")
    url = (params.get("url") or "").strip()
    if url:
        try:
            return load_image_from_url(url), url
        except Exception as e:
            raise ApiError(f"Impossible de télécharger l'image : {e}")
    raise ApiError("Fournissez une image ('image') ou une URL ('url').")


@app.route("/mirflickr/search/image", methods=["POST"])
def mirflickr_image_search():
    """
    Visual search on MIRFLICKR-1M from an uploaded image or URL.
    The query image is converted on the fly to the chosen MPEG-7 descriptor
    (edge is implemented; homo is not — a published image's precomputed
    descriptor would be needed).
    """
    from mirflickr_index import get as get_mir
    from mpeg7_edge import edge_histogram
    params = _params()
    name = params.get("descriptor", "edge")
    if name != "edge":
        raise ApiError("Only 'edge' supports on-the-fly extraction; "
                       "use /mirflickr/similar with a photo_id for 'homo'.")
    size = _int_param(params, "size", DEFAULT_RESULTS)

    img, src = _mirflickr_query_image()
    t0 = time.perf_counter()
    q = edge_histogram(img)
    extract_ms = (time.perf_counter() - t0) * 1000

    mir = get_mir(name)
    out = mir.search(q, k=size)

    # Enrich with ES metadata (one _mget per request)
    ids = [str(r["photo_id"]) for r in out["results"]]
    if ids:
        docs = es.mget(index=MIRFLICKR_INDEX, body={"ids": ids})["docs"]
        meta_by_id = {int(d["_id"]): d.get("_source", {})
                      for d in docs if d.get("found")}
        for r in out["results"]:
            m = meta_by_id.get(r["photo_id"], {})
            r["title"] = m.get("title", "")
            r["tags"] = m.get("tags", "")
            r["url"] = m.get("url", f"im{r['photo_id']}.jpg")

    return jsonify({
        "descriptor": name,
        "source": "url" if src else "upload",
        "query_url": src,
        "count": len(out["results"]),
        "extract_ms": extract_ms,
        **out,
    })


@app.route("/mirflickr/similar", methods=["GET"])
def mirflickr_similar():
    """Images MIRFLICKR les plus proches d'une photo_id, par descripteur MPEG-7."""
    from mirflickr_index import get as get_mir
    try:
        pid = int(request.args.get("photo_id", ""))
    except ValueError:
        raise ApiError("'photo_id' entier requis.")
    name = request.args.get("descriptor", "edge")
    if name not in ("edge", "homo"):
        raise ApiError("'descriptor' doit être edge ou homo.")
    size = _int_param(request.args, "size", DEFAULT_RESULTS)
    mir = get_mir(name)
    out = mir.search(mir.vector(pid), k=size, exclude=pid)
    # Enrichit chaque résultat avec les métadonnées texte (une seule requête ES _mget)
    ids = [str(r["photo_id"]) for r in out["results"]]
    if ids:
        docs = es.mget(index=MIRFLICKR_INDEX, body={"ids": ids})["docs"]
        meta_by_id = {int(d["_id"]): d.get("_source", {}) for d in docs if d.get("found")}
        for r in out["results"]:
            m = meta_by_id.get(r["photo_id"], {})
            r["title"] = m.get("title", "")
            r["tags"] = m.get("tags", "")
            r["url"] = m.get("url", f"im{r['photo_id']}.jpg")
    return jsonify({"photo_id": pid, "descriptor": name,
                    "count": len(out["results"]), **out})


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
