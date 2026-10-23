"""Interface Streamlit — moteur de recherche d'images (TBIR + CBIR) et comparaison des modèles."""

import io
import os
import random

import altair as alt
import pandas as pd
import requests
import streamlit as st
from PIL import Image

API_URL = os.getenv("API_URL", "http://localhost:5000")
IMAGE_TYPES = ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"]

# Couleurs fixes par modèle (ordre catégoriel : slot 1 bleu, slot 2 orange)
MODEL_COLORS = {"inception_lbp": "#2a78d6", "vgg16": "#eb6834"}

st.set_page_config(
    page_title="Moteur de Recherche d'Images",
    page_icon="🔍",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; }
      .hero h1 { margin-bottom: 0.2rem; }
      .hero p { color: #6b6a66; margin-top: 0; font-size: 1.05rem; }
      .model-tag { display: inline-block; width: 0.8rem; height: 0.8rem;
                   border-radius: 3px; margin-right: 0.4rem; vertical-align: -1px; }
      div[data-testid="stImage"] img { border-radius: 6px; object-fit: cover; aspect-ratio: 4 / 3; }
      div[data-testid="stMetricValue"] { font-size: 1.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ======================================================================
# Accès à l'API
# ======================================================================

def api(method: str, path: str, timeout: int = 120, **kwargs):
    """Appel API ; affiche l'erreur et retourne None en cas d'échec."""
    try:
        resp = requests.request(method, f"{API_URL}{path}", timeout=timeout, **kwargs)
    except requests.RequestException as e:
        st.error(f"API injoignable ({API_URL}) : {e}")
        return None
    if not resp.ok:
        try:
            msg = resp.json().get("error") or resp.json().get("detail") or resp.text
        except ValueError:
            msg = resp.text
        st.error(f"Erreur {resp.status_code} : {msg}")
        return None
    return resp.json()


@st.cache_data(ttl=15, show_spinner=False)
def get_stats():
    try:
        return requests.get(f"{API_URL}/stats", timeout=10).json()
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_models():
    try:
        return requests.get(f"{API_URL}/models", timeout=10).json()["models"]
    except Exception:
        return {
            "inception_lbp": {"label": "InceptionV3 + LBP", "description": "", "dims": 2058},
            "vgg16": {"label": "VGG16", "description": "", "dims": 512},
        }


@st.cache_data(ttl=300, show_spinner=False)
def get_dataset(class_name: str, size: int = 500):
    params = {"size": size}
    if class_name:
        params["class"] = class_name
    try:
        return requests.get(f"{API_URL}/dataset/images", params=params, timeout=15).json()["images"]
    except Exception:
        return []


@st.cache_data(max_entries=2000, show_spinner=False)
def thumbnail(image_path: str, width: int = 360):
    """Vignette d'une image de la base, récupérée côté serveur (le navigateur
    ne peut pas résoudre l'hôte interne Docker 'backend')."""
    try:
        resp = requests.get(f"{API_URL}/images/{image_path}", timeout=15)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        img.thumbnail((width, width))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    except Exception:
        return None


def model_label(model: str) -> str:
    return get_models().get(model, {}).get("label", model)


def model_tag(model: str) -> str:
    color = MODEL_COLORS.get(model, "#888")
    return f'<span class="model-tag" style="background:{color}"></span>{model_label(model)}'


# ======================================================================
# Composants
# ======================================================================

def show_image(image_path: str):
    data = thumbnail(image_path)
    if data:
        st.image(data, use_container_width=True)
    else:
        st.warning("Image indisponible")


def image_results_grid(results, query_class=None, n_cols=5, key="grid", on_similar=None):
    """Grille de résultats CBIR ; pertinence en vert/rouge si la classe attendue est connue."""
    if not results:
        st.info("Aucun résultat.")
        return
    cols = st.columns(n_cols)
    for i, r in enumerate(results):
        with cols[i % n_cols]:
            with st.container(border=True):
                show_image(r["image_path"])
                cls = r.get("class_name", "")
                if query_class:
                    badge = ":green-background[✓ " + cls + "]" if cls == query_class \
                        else ":red-background[✗ " + cls + "]"
                else:
                    badge = f":gray-background[{cls}]"
                dist = r.get("distance")
                st.markdown(
                    f"**#{i + 1}** {badge}  \n"
                    f"<small>dist. L2 {dist:.2f} · score {r['score']:.3f}</small>"
                    if dist is not None else f"**#{i + 1}** {badge}",
                    unsafe_allow_html=True,
                )
                if on_similar:
                    st.button(
                        "Images similaires", key=f"{key}-sim-{i}",
                        on_click=on_similar, args=(r["image_path"],),
                        use_container_width=True,
                    )


def query_picker(key: str, allow_class_hint: bool = True):
    """
    Choix de l'image requête : base d'images, upload ou URL.
    Retourne (kind, value, query_class, preview) ou None.
    kind ∈ {"path", "upload", "url"}.
    """
    stats = get_stats() or {}
    classes = sorted((stats.get("classes") or {}).keys())

    st.session_state.setdefault(f"{key}-source", "Base d'images")
    source = st.segmented_control(
        "Source de l'image requête",
        ["Base d'images", "Téléverser", "URL"],
        key=f"{key}-source",
    ) or "Base d'images"

    if source == "Base d'images":
        if not classes:
            st.warning("Aucune image indexée. Voir la page « À propos » pour indexer la base.")
            return None
        state_key = f"{key}-path"
        cls = st.selectbox("Classe", classes, key=f"{key}-class")
        images = get_dataset(cls)
        paths = [im["image_path"] for im in images]
        if st.session_state.get(state_key) not in paths:
            st.session_state[state_key] = paths[0] if paths else None
        c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
        with c2:
            if st.button("🎲", key=f"{key}-rand", help="Image aléatoire de cette classe",
                         use_container_width=True) and paths:
                st.session_state[state_key] = random.choice(paths)
        with c1:
            path = st.selectbox(
                "Image", paths, key=state_key,
                format_func=lambda p: p.split("/", 1)[-1],
            )
        if not path:
            return None
        return "path", path, cls, thumbnail(path, 480)

    query_class = None
    if source == "Téléverser":
        up = st.file_uploader("Image", type=IMAGE_TYPES, key=f"{key}-upload")
        if up is None:
            return None
        value, preview = up, up.getvalue()
    else:
        url = st.text_input("URL de l'image", placeholder="https://...", key=f"{key}-url").strip()
        if not url:
            return None
        value, preview = url, url

    if allow_class_hint and classes:
        hint = st.selectbox(
            "Classe attendue (optionnel — active le calcul de la précision)",
            ["—"] + classes, key=f"{key}-hint",
        )
        query_class = None if hint == "—" else hint
    return ("upload" if source == "Téléverser" else "url"), value, query_class, preview


def request_kwargs(kind: str, value, extra: dict):
    """Paramètres requests pour /compare ou /search selon la source."""
    if kind == "upload":
        return {"files": {"image": (value.name, value.getvalue(), value.type)}, "data": extra}
    if kind == "url":
        return {"json": {"url": value, **extra}}
    return {"data": {"path": value, **extra}}


# ======================================================================
# Pages
# ======================================================================

def page_home():
    st.markdown(
        '<div class="hero"><h1>🔍 Moteur de Recherche d\'Images</h1>'
        "<p>Recherche par texte (TBIR) et par contenu visuel (CBIR) sur Elasticsearch — "
        "avec comparaison InceptionV3 + LBP vs VGG16.</p></div>",
        unsafe_allow_html=True,
    )

    health = None
    try:
        health = requests.get(f"{API_URL}/health", timeout=5).json()
    except Exception:
        pass
    stats = get_stats()

    if not health or health.get("status") != "ok":
        st.error("Le backend ou Elasticsearch ne répond pas. Vérifiez `docker compose ps`.")
        return

    classes = stats.get("classes", {})
    c1, c2, c3, c4 = st.columns(4)
    for col, label, value in [
        (c1, "Elasticsearch", health["elasticsearch"]),
        (c2, "Images indexées", stats["models"].get("inception_lbp", {}).get("images", 0)),
        (c3, "Classes", len(classes)),
        (c4, "Documents texte (Flickr)", stats["text_documents"]),
    ]:
        with col.container(border=True):
            st.metric(label, value)

    st.subheader("Approches comparées")
    cols = st.columns(len(get_models()))
    for col, (name, cfg) in zip(cols, get_models().items()):
        with col.container(border=True):
            st.markdown(f"#### {model_tag(name)}", unsafe_allow_html=True)
            st.caption(cfg.get("description", ""))
            st.markdown(
                f"Dimension du vecteur : **{cfg['dims']}**  \n"
                f"Images indexées : **{stats['models'].get(name, {}).get('images', 0)}**"
            )

    if classes:
        st.subheader("Répartition de la base d'images")
        df = pd.DataFrame({"Classe": list(classes), "Images": list(classes.values())})
        chart = (
            alt.Chart(df)
            .mark_bar(cornerRadiusEnd=4, color=MODEL_COLORS["inception_lbp"], size=28)
            .encode(
                x=alt.X("Classe:N", sort="-y", title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Images:Q", title="Nombre d'images"),
                tooltip=["Classe", "Images"],
            )
            .properties(height=260)
        )
        st.altair_chart(chart, use_container_width=True)

    missing = []
    if not classes:
        missing.append("la base d'images n'est pas indexée")
    if not stats["text_documents"]:
        missing.append("les métadonnées Flickr ne sont pas indexées (recherche textuelle vide)")
    if missing:
        st.info("À faire : " + " ; ".join(missing) + ". Voir la page **À propos**.")


def page_text_search():
    st.header("📝 Recherche textuelle (TBIR)")
    st.caption("Recherche multi-champs (titre ×3, tags ×2, description) avec tolérance aux fautes.")

    with st.form("text-search"):
        c1, c2 = st.columns([4, 1])
        query = c1.text_input("Requête", placeholder="ex : sunset beach", label_visibility="collapsed")
        size = c2.number_input("Résultats", 1, 100, 20, label_visibility="collapsed")
        submitted = st.form_submit_button("Rechercher", type="primary")

    if submitted and query.strip():
        with st.spinner("Recherche en cours..."):
            st.session_state["text-results"] = api(
                "GET", "/search/text", params={"q": query, "size": size}
            )

    index_empty = (get_stats() or {}).get("text_documents") == 0
    if index_empty:
        st.info("L'index texte est vide : placez `photo_metadata.csv` dans `data/` "
                "puis lancez `scripts/index_text.py`.")

    data = st.session_state.get("text-results")
    if not data:
        return
    if not data["count"]:
        if not index_empty:
            st.warning(f"Aucun résultat pour « {data['query']} ».")
        return

    st.success(f"{data['count']} résultat(s) pour « {data['query']} » "
               f"en {data.get('search_ms', 0):.0f} ms")
    cols = st.columns(4)
    for i, r in enumerate(data["results"]):
        with cols[i % 4]:
            with st.container(border=True):
                st.image(r["url"], use_container_width=True)
                st.markdown(f"**{r.get('title') or 'Sans titre'}**")
                hl = r.get("highlight", {})
                snippet = (hl.get("description") or hl.get("tags") or [""])[0]
                if snippet:
                    st.caption("…" + snippet + "…")
                tags = (r.get("tags") or "").split()[:6]
                if tags:
                    st.markdown(" ".join(f":gray-background[{t}]" for t in tags))
                st.caption(f"Score BM25 : {r['score']:.2f}")


def page_image_search():
    st.header("🖼️ Recherche par image (CBIR)")

    def set_query(path):
        cls = path.split("/", 1)[0]
        st.session_state["img-source"] = "Base d'images"
        st.session_state["img-class"] = cls
        st.session_state["img-path"] = path
        st.session_state["img-auto"] = True

    left, right = st.columns([1, 2], gap="large")
    with left:
        models = get_models()
        model = st.radio(
            "Modèle", list(models), format_func=model_label, horizontal=True, key="img-model"
        )
        size = st.slider("Nombre de résultats", 1, 50, 10, key="img-size")
        picked = query_picker("img")
        launch = st.button("Rechercher des images similaires", type="primary",
                           disabled=picked is None, use_container_width=True)
    with right:
        if picked:
            st.image(picked[3], caption="Image requête", width=320)

    if picked and (launch or st.session_state.pop("img-auto", False)):
        kind, value, query_class, _ = picked
        with st.spinner(f"Extraction ({model_label(model)}) et recherche..."):
            if kind == "path":
                data = api("GET", "/search/similar",
                           params={"path": value, "size": size, "model": model})
            elif kind == "upload":
                data = api("POST", "/search/image",
                           **request_kwargs(kind, value, {"size": size, "model": model}))
            else:
                data = api("POST", "/search/url",
                           **request_kwargs(kind, value, {"size": size, "model": model}))
        st.session_state["img-results"] = (data, query_class) if data else None

    stored = st.session_state.get("img-results")
    if not stored:
        return
    data, query_class = stored
    st.divider()
    n_rel = sum(r["class_name"] == query_class for r in data["results"]) if query_class else None
    extract = f"extraction {data['extract_ms']:.0f} ms" if data["extract_ms"] else "vecteur déjà indexé"
    summary = f"{data['count']} résultat(s) · {model_label(data['model'])} · " \
              f"{extract} · recherche {data['search_ms']:.0f} ms"
    if n_rel is not None:
        summary += f" · précision {n_rel}/{data['count']}"
    st.success(summary)
    image_results_grid(data["results"], query_class, key="img", on_similar=set_query)


def page_compare():
    st.header("⚖️ Comparaison : InceptionV3 + LBP vs VGG16")
    st.markdown(
        f"{model_tag('inception_lbp')} &nbsp;&nbsp;vs&nbsp;&nbsp; {model_tag('vgg16')}",
        unsafe_allow_html=True,
    )
    tab_query, tab_bench = st.tabs(["Requête côte à côte", "Évaluation globale"])
    with tab_query:
        compare_query()
    with tab_bench:
        compare_benchmark()


def compare_query():
    c1, c2 = st.columns([1, 2], gap="large")
    with c1:
        size = st.slider("Nombre de résultats (k)", 1, 30, 10, key="cmp-size")
        picked = query_picker("cmp")
        launch = st.button("Comparer", type="primary", disabled=picked is None,
                           use_container_width=True)
    with c2:
        if picked:
            st.image(picked[3], caption="Image requête", width=320)

    if picked and launch:
        kind, value, query_class, _ = picked
        extra = {"size": size}
        if query_class and kind != "path":
            extra["query_class"] = query_class
        with st.spinner("Extraction des caractéristiques avec les deux modèles..."):
            st.session_state["cmp-results"] = api("POST", "/compare", **request_kwargs(kind, value, extra))

    data = st.session_state.get("cmp-results")
    if not data:
        st.info("Choisissez une image puis lancez la comparaison. Avec une image de la base, "
                "la classe est connue : la précision et l'AP sont calculées automatiquement.")
        return

    st.divider()
    query_class = data.get("query_class")
    models = list(data["models"])
    ref = data["models"].get("inception_lbp")

    cols = st.columns(len(models))
    for col, m in zip(cols, models):
        res = data["models"][m]
        with col.container(border=True):
            st.markdown(f"### {model_tag(m)}", unsafe_allow_html=True)
            k1, k2, k3, k4 = st.columns(4)
            metrics = res.get("metrics")
            is_ref = m == "inception_lbp" or ref is None or not ref.get("metrics")
            if metrics:
                ref_m = ref["metrics"] if not is_ref else None
                k1.metric(f"Précision@{data['size']}", f"{metrics['precision']:.0%}",
                          None if ref_m is None else f"{(metrics['precision'] - ref_m['precision']) * 100:+.0f} pts")
                k2.metric("AP", f"{metrics['ap']:.3f}",
                          None if ref_m is None else f"{metrics['ap'] - ref_m['ap']:+.3f}")
            else:
                k1.metric("Précision", "—")
                k2.metric("AP", "—")
            k3.metric("Extraction", f"{res['extract_ms']:.0f} ms" if res["extract_ms"] else "indexé")
            k4.metric("Recherche", f"{res['search_ms']:.0f} ms")

    overlap = len(data.get("overlap", []))
    st.caption(f"Résultats communs aux deux modèles : **{overlap} / {data['size']}**"
               + ("" if query_class else " — indiquez une classe attendue pour obtenir la précision."))

    cols = st.columns(len(models), gap="large")
    for col, m in zip(cols, models):
        with col:
            st.markdown(f"**{model_tag(m)}**", unsafe_allow_html=True)
            image_results_grid(data["models"][m]["results"], query_class, n_cols=3, key=f"cmp-{m}")


def compare_benchmark():
    st.markdown(
        "Chaque image de la base sert de requête (elle-même exclue des résultats) ; "
        "un résultat est **pertinent** s'il appartient à la même classe. "
        "Les deux modèles sont évalués sur les mêmes requêtes, en recherche approchée (index Elastiknn L2 LSH) et exacte."
    )
    with st.expander("Relancer l'évaluation"):
        with st.form("bench"):
            c1, c2, c3 = st.columns(3)
            k = c1.number_input("k (résultats par requête)", 1, 50, 10)
            per_class = c2.number_input("Requêtes par classe (0 = toutes)", 0, 10000, 0)
            candidates = c3.number_input("Candidats LSH", 10, 1000, 50)
            run = st.form_submit_button("Lancer l'évaluation", type="primary")
        if run:
            with st.spinner("Évaluation en cours (une requête par image et par modèle)..."):
                report = api("POST", "/benchmark/run", timeout=600, data={
                    "k": k, "per_class": per_class, "candidates": candidates,
                })
            if report:
                st.session_state["bench-report"] = report
                get_stats.clear()

    report = st.session_state.get("bench-report")
    if report is None:
        try:
            resp = requests.get(f"{API_URL}/benchmark", timeout=10)
            report = resp.json() if resp.ok else None
        except Exception:
            report = None
    if not report or not report.get("models"):
        st.info("Aucun rapport d'évaluation : lancez-la ci-dessus (ou `scripts/evaluate.py`).")
        return
    st.session_state["bench-report"] = report
    k = report["k"]
    models = list(report["models"])

    mode = st.segmented_control(
        "Type de recherche",
        ["Approchée (LSH)", "Exacte"],
        default="Approchée (LSH)",
        key="bench-mode",
        help="LSH : index Elastiknn tel qu'utilisé par le moteur (aléatoire, rapide). "
             "Exacte : kNN exhaustif — mesure la qualité pure des descripteurs.",
    ) or "Approchée (LSH)"
    exact = mode == "Exacte" and all("exact" in report["models"][m] for m in models)
    # Métriques du mode choisi (les infos communes restent au premier niveau)
    view = {m: {**report["models"][m], **(report["models"][m]["exact"] if exact else {})}
            for m in models}

    st.caption(
        f"{report['n_queries']} requêtes · {report['n_images']} images · "
        f"{len(report['classes'])} classes · k = {k} · {report['candidates']} candidats LSH · "
        f"calculé le {report['generated_at'].replace('T', ' ')[:16]} UTC"
    )

    # --- Indicateurs clés
    ref = view.get("inception_lbp")
    cols = st.columns(len(models))
    for col, m in zip(cols, models):
        r = view[m]
        is_ref = m == "inception_lbp" or ref is None
        delta = (lambda key, pts=False: None if is_ref else (
            f"{(r[key] - ref[key]) * 100:+.1f} pts" if pts else f"{r[key] - ref[key]:+.3f}"))
        with col.container(border=True):
            st.markdown(f"#### {model_tag(m)}", unsafe_allow_html=True)
            a, b, c = st.columns(3)
            a.metric(f"Précision@{k}", f"{r['precision']:.1%}", delta("precision", True))
            b.metric("mAP", f"{r['map']:.3f}", delta("map"))
            c.metric("P@1", f"{r['p_at_1']:.1%}", delta("p_at_1", True))
            a, b, c = st.columns(3)
            a.metric("Requête ES", f"{r['mean_query_ms']:.0f} ms")
            ext = r.get("mean_extract_ms")
            b.metric("Extraction", f"{ext:.0f} ms" if ext else "—")
            c.metric("Dimension", r["dims"])

    labels = [view[m]["label"] for m in models]
    color = alt.Color(
        "Modèle:N",
        scale=alt.Scale(domain=labels, range=[MODEL_COLORS.get(m, "#888") for m in models]),
        legend=alt.Legend(orient="top", title=None),
    )

    # --- Par classe
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.subheader("Performance par classe")
        metric = st.segmented_control(
            "Métrique", [f"Précision@{k}", "AP"], default=f"Précision@{k}", key="bench-metric",
            label_visibility="collapsed",
        ) or f"Précision@{k}"
        field = "precision" if metric.startswith("Précision") else "ap"
        rows = [
            {"Classe": cls, "Modèle": view[m]["label"], metric: v[field]}
            for m in models for cls, v in view[m]["per_class"].items()
        ]
        chart = (
            alt.Chart(pd.DataFrame(rows))
            .mark_bar(cornerRadiusEnd=4, size=18)
            .encode(
                x=alt.X("Classe:N", title=None, axis=alt.Axis(labelAngle=0)),
                xOffset=alt.XOffset("Modèle:N", sort=labels),
                y=alt.Y(f"{metric}:Q", scale=alt.Scale(domain=[0, 1]),
                        axis=alt.Axis(format="%" if field == "precision" else ".1f")),
                color=color,
                tooltip=["Classe", "Modèle",
                         alt.Tooltip(f"{metric}:Q", format=".1%" if field == "precision" else ".3f")],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)

    # --- Précision selon le rang
    with c2:
        st.subheader("Précision selon le rang")
        st.caption("Précision moyenne des n premiers résultats (P@n).")
        rows = [
            {"Rang": i + 1, "Modèle": view[m]["label"], "Précision": p}
            for m in models for i, p in enumerate(view[m]["precision_curve"])
        ]
        base = alt.Chart(pd.DataFrame(rows)).encode(
            x=alt.X("Rang:Q", scale=alt.Scale(domain=[1, k]), axis=alt.Axis(tickMinStep=1)),
            y=alt.Y("Précision:Q", scale=alt.Scale(zero=False), axis=alt.Axis(format="%")),
            color=color,
            tooltip=["Modèle", "Rang", alt.Tooltip("Précision:Q", format=".1%")],
        )
        chart = (base.mark_line(strokeWidth=2) + base.mark_point(size=60, filled=True)).properties(height=320)
        st.altair_chart(chart, use_container_width=True)

    # --- Tableau détaillé
    st.subheader("Tableau détaillé")
    table = []
    for cls in report["classes"]:
        row = {"Classe": cls, "Images": report["classes"][cls]}
        for m in models:
            pc = view[m]["per_class"].get(cls, {})
            row[f"P@{k} — {report['models'][m]['label']}"] = pc.get("precision")
            row[f"AP — {report['models'][m]['label']}"] = pc.get("ap")
        table.append(row)
    df = pd.DataFrame(table)
    p_cols = [c for c in df.columns if c.startswith("P@")]
    df[p_cols] = df[p_cols] * 100
    config = {c: st.column_config.NumberColumn(format="%.1f %%") for c in p_cols}
    config.update({c: st.column_config.NumberColumn(format="%.3f")
                   for c in df.columns if c.startswith("AP")})
    st.dataframe(df, column_config=config, use_container_width=True, hide_index=True)

    # --- Lecture
    if len(models) == 2 and ref:
        other = view[models[1]]
        diff = (ref["map"] - other["map"]) * 100
        winner = ref["label"] if diff >= 0 else other["label"]
        st.info(
            f"**Lecture :** sur cette base, **{winner}** obtient le meilleur mAP "
            f"(écart de {abs(diff):.1f} points). VGG16 produit des vecteurs 4× plus compacts "
            f"({other['dims']} vs {ref['dims']} dimensions), ce qui réduit la taille de l'index "
            f"({other['index_size_mb']:.1f} Mo vs {ref['index_size_mb']:.1f} Mo)."
        )


def page_about():
    st.header("ℹ️ À propos")
    st.markdown(
        """
### Architecture
- **Elasticsearch 7.17 + Elastiknn** : un index texte (`flickrphotos`) et un index vectoriel
  par modèle (`images_data`, `images_vgg16`), recherche approchée L2 LSH.
- **Backend Flask** : extraction des caractéristiques et API REST.
- **Frontend Streamlit** : cette interface.

### Approches CBIR comparées
| | InceptionV3 + LBP (notre approche) | VGG16 (référence) |
|---|---|---|
| Entrée | 299 × 299 | 224 × 224 |
| Descripteur | CNN 2048 + texture LBP 10 | CNN 512 |
| Couche | global average pooling (mixed10) | global average pooling (block5) |
| Similarité | distance L2 | distance L2 |

### Mettre à jour les données
```bash
# Métadonnées Flickr (data/photo_metadata.csv)
docker exec backend-search-engine python /scripts/index_text.py
# Images (data/bdimage/<classe>/...) : extraction des deux modèles, indexation, évaluation
docker exec backend-search-engine python /scripts/extract_features.py
docker exec backend-search-engine python /scripts/index_images.py
docker exec backend-search-engine python /scripts/evaluate.py
```
"""
    )


# ======================================================================
# Navigation
# ======================================================================

pages = st.navigation([
    st.Page(page_home, title="Accueil", icon="🏠", default=True),
    st.Page(page_text_search, title="Recherche textuelle", icon="📝", url_path="texte"),
    st.Page(page_image_search, title="Recherche par image", icon="🖼️", url_path="image"),
    st.Page(page_compare, title="Comparaison des modèles", icon="⚖️", url_path="comparaison"),
    st.Page(page_about, title="À propos", icon="ℹ️", url_path="a-propos"),
])
pages.run()
