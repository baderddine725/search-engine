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

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --ink:     #16161a;
  --ink-2:   #3c3c42;
  --muted:   #74737a;
  --rule:    #e6e3dc;
  --rule-2:  #f1ede4;
  --paper:   #faf7f0;
  --paper-2: #f3eee2;
  --accent:  #7b2e3a;
  --accent-soft: #f3e0e3;
  --gold:    #c9a24b;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--paper);
  color: var(--ink);
}
html, body, [class*="st-"] {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  color: var(--ink);
}
h1, h2, h3, h4, .serif {
  font-family: 'Fraunces', 'Iowan Old Style', Georgia, serif;
  font-weight: 500; letter-spacing: -0.015em; color: var(--ink);
}
code, pre, kbd, .mono { font-family: 'JetBrains Mono', ui-monospace, monospace; }

.block-container { padding-top: 2.4rem; padding-bottom: 5rem; max-width: 1200px; }

section[data-testid="stSidebar"] {
  background: #f6f1e5;
  border-right: 1px solid var(--rule);
}
section[data-testid="stSidebar"] * { font-family: 'Inter', sans-serif; }

[data-testid="stHeader"] { background: transparent; }

.page-head {
  margin-bottom: 2rem;
  position: relative;
}
.page-head .eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: .68rem; letter-spacing: .22em; text-transform: uppercase;
  color: var(--accent); font-weight: 500; margin-bottom: .9rem;
  display: inline-block; padding-bottom: .35rem;
  border-bottom: 1px solid var(--accent);
}
.page-head h1 {
  font-size: 2.9rem; margin: 0; line-height: 1.05;
  font-weight: 500; font-variant-ligatures: common-ligatures;
}
.page-head p {
  color: var(--ink-2); margin: .9rem 0 0; max-width: 62ch;
  font-size: 1.02rem; line-height: 1.6;
}
.rule-ornament {
  display: flex; align-items: center; gap: .6rem;
  margin: 2rem 0 1.4rem 0;
}
.rule-ornament::before, .rule-ornament::after {
  content: ''; flex: 1; height: 1px; background: var(--rule);
}
.rule-ornament span {
  color: var(--accent); font-family: 'Fraunces', serif;
  font-style: italic; font-size: .95rem;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
  border: 1px solid var(--rule) !important;
  border-radius: 6px !important;
  background: #fffdf7;
  box-shadow: 0 1px 0 rgba(22,22,26,.03), 0 12px 24px -18px rgba(22,22,26,.14);
  transition: box-shadow .18s ease, transform .18s ease, border-color .18s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color: #d6d1c2 !important;
  box-shadow: 0 1px 0 rgba(22,22,26,.04), 0 20px 36px -20px rgba(22,22,26,.18);
  transform: translateY(-1px);
}

div[data-testid="stImage"] img {
  border-radius: 4px; object-fit: cover; aspect-ratio: 4 / 3;
  box-shadow: inset 0 0 0 1px rgba(22,22,26,.05);
  transition: transform .3s ease;
}
div[data-testid="stImage"]:hover img { transform: scale(1.01); }

.stat-card {
  position: relative;
  padding: 1.1rem 1.2rem 1.1rem 1.4rem;
  background: #fffdf7;
  border: 1px solid var(--rule);
  border-radius: 6px;
  box-shadow: 0 1px 0 rgba(22,22,26,.03);
}
.stat-card::before {
  content: ''; position: absolute; left: 0; top: 14%; bottom: 14%;
  width: 2px; background: var(--accent);
}
.stat-card .label {
  font-family: 'JetBrains Mono', monospace;
  font-size: .66rem; letter-spacing: .18em; text-transform: uppercase;
  color: var(--muted); margin-bottom: .35rem;
}
.stat-card .value {
  font-family: 'Fraunces', serif; font-size: 2rem; font-weight: 500;
  line-height: 1.1; color: var(--ink);
  font-variant-numeric: lining-nums tabular-nums;
}
.stat-card .unit {
  font-size: .78rem; color: var(--muted); margin-left: .3rem;
  font-family: 'Inter', sans-serif;
}

.approach {
  padding: 1.6rem 1.8rem;
  background: #fffdf7;
  border: 1px solid var(--rule);
  border-radius: 6px;
  position: relative; overflow: hidden;
  box-shadow: 0 1px 0 rgba(22,22,26,.03), 0 20px 36px -24px rgba(22,22,26,.15);
}
.approach::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: var(--accent);
}
.approach .idx {
  font-family: 'Fraunces', serif; font-style: italic;
  font-size: .9rem; color: var(--accent);
}
.approach h4 {
  font-family: 'Fraunces', serif; font-weight: 500;
  font-size: 1.5rem; margin: .3rem 0 .6rem 0; letter-spacing: -0.015em;
}
.approach .desc { color: var(--ink-2); font-size: .92rem; line-height: 1.55; }
.approach .meta {
  display: flex; gap: 1.4rem; margin-top: 1rem;
  padding-top: .9rem; border-top: 1px solid var(--rule-2);
  font-size: .78rem; color: var(--muted);
}
.approach .meta b { color: var(--ink); font-weight: 600; font-variant-numeric: tabular-nums; }

.rc-rank {
  font-family: 'Fraunces', serif; font-size: 1.1rem; color: var(--muted);
  font-variant-numeric: tabular-nums; font-style: italic;
  margin-right: .5rem; min-width: 1.8rem; display: inline-block;
}
.rc-rank.top { color: var(--accent); font-weight: 600; font-style: normal; }

.rc-chip {
  display: inline-block; font-size: .68rem; font-weight: 500;
  padding: .18rem .55rem; border-radius: 999px; letter-spacing: .04em;
  text-transform: uppercase;
}
.rc-chip.ok      { color: #2d5a3d; border: 1px solid #bcd4c4; background: #eff6f0; }
.rc-chip.miss    { color: var(--accent); border: 1px solid #e3c3c7; background: var(--accent-soft); }
.rc-chip.neutral { color: var(--ink-2); border: 1px solid var(--rule); background: var(--paper-2); }

.rc-score-row { display: flex; align-items: center; gap: .55rem; margin-top: .5rem; }
.rc-score-row small { color: var(--muted); font-variant-numeric: tabular-nums; font-size: .72rem; }
.rc-bar {
  flex: 1; height: 3px; background: var(--rule-2); border-radius: 999px; overflow: hidden;
}
.rc-bar > span { display: block; height: 100%; background: var(--ink); border-radius: 999px; }
.rc-bar.warm > span { background: var(--accent); }

.tag-pill {
  display: inline-block; margin: 3px 4px 0 0; padding: 2px 8px;
  font-size: .7rem; color: var(--ink-2);
  border: 1px solid var(--rule); border-radius: 999px;
  background: #fffdf7;
}

div.stButton > button {
  border-radius: 999px; font-weight: 500; letter-spacing: .02em;
  padding: .55rem 1.4rem;
  border: 1px solid var(--ink); background: transparent; color: var(--ink);
  transition: all .15s ease; font-size: .9rem;
}
div.stButton > button:hover { background: var(--ink); color: var(--paper); }
div.stButton > button[kind="primary"] {
  background: var(--ink); color: var(--paper); border-color: var(--ink);
  box-shadow: 0 6px 14px -8px rgba(22,22,26,.4);
}
div.stButton > button[kind="primary"]:hover {
  background: var(--accent); border-color: var(--accent);
  box-shadow: 0 10px 20px -8px rgba(123,46,58,.5);
}

input[type="text"], textarea, [data-baseweb="input"] input {
  border-radius: 6px !important;
}

hr { border: 0; border-top: 1px solid var(--rule); margin: 2.4rem 0; }

.result-caption {
  font-size: .85rem; color: var(--ink); line-height: 1.35; margin-top: .55rem;
  display: flex; align-items: baseline; gap: .3rem; flex-wrap: wrap;
}
.muted { color: var(--muted); font-size: .72rem; }

.callout {
  border-left: 2px solid var(--accent); padding: .3rem 0 .3rem 1.1rem;
  margin: 1.2rem 0; color: var(--ink-2); font-size: .95rem;
  background: linear-gradient(90deg, var(--accent-soft) 0%, transparent 20%);
}

[data-testid="stMetricValue"] { font-family: 'Fraunces', serif; font-weight: 500;
    font-size: 2rem; color: var(--ink); font-variant-numeric: lining-nums tabular-nums; }
[data-testid="stMetricLabel"] { font-family: 'JetBrains Mono', monospace;
    font-size: .68rem; letter-spacing: .18em; text-transform: uppercase;
    color: var(--muted); font-weight: 500; }

[data-baseweb="tab-list"] { border-bottom: 1px solid var(--rule) !important; gap: 1.5rem; }
[data-baseweb="tab"] {
  font-family: 'Fraunces', serif !important; font-size: 1.02rem !important;
  color: var(--muted) !important; padding: .3rem 0 !important;
  background: transparent !important;
}
[data-baseweb="tab"][aria-selected="true"] {
  color: var(--ink) !important;
  border-bottom: 2px solid var(--accent) !important;
}
</style>
"""

# st.html keeps the block as HTML (plus sûr que st.markdown pour les gros <style>)
try:
    st.html(_CSS)
except Exception:
    st.markdown(_CSS, unsafe_allow_html=True)


def _rank_class(i: int) -> str:
    return "top" if i == 0 else ""


def page_head(eyebrow: str, title: str, subtitle: str = ""):
    """En-tête éditorial à gauche (surtitre, titre serif, chapô)."""
    sub = f'<p>{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="page-head">'
        f'<div class="eyebrow">{eyebrow}</div>'
        f'<h1>{title}</h1>{sub}</div>',
        unsafe_allow_html=True,
    )


def _score_bar(score: float, warm: bool = False) -> str:
    pct = max(0.0, min(1.0, float(score))) * 100
    cls = "rc-bar warm" if warm else "rc-bar"
    return f'<div class="{cls}"><span style="width:{pct:.1f}%"></span></div>'


def _tag_pills(tags: str, limit: int = 6) -> str:
    toks = [t for t in (tags or "").split() if t][:limit]
    return " ".join(f'<span class="tag-pill">{t}</span>' for t in toks)


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
    """Grille de résultats CBIR ; pertinence éditoriale, rang en chiffres romains discrets."""
    if not results:
        st.info("Aucun résultat.")
        return
    scores = [float(r.get("score", 0.0) or 0.0) for r in results]
    s_max = max(scores) or 1.0
    cols = st.columns(n_cols)
    for i, r in enumerate(results):
        with cols[i % n_cols]:
            with st.container(border=True):
                show_image(r["image_path"])
                cls = r.get("class_name", "")
                if query_class:
                    chip = (f'<span class="rc-chip ok">{cls}</span>'
                            if cls == query_class else
                            f'<span class="rc-chip miss">{cls}</span>')
                else:
                    chip = f'<span class="rc-chip neutral">{cls or "—"}</span>'
                dist = r.get("distance")
                score = scores[i]
                bar = _score_bar(score / s_max) if score else ""
                dist_txt = f" · dist {dist:.3f}" if dist is not None else ""
                st.markdown(
                    f'<div class="result-caption">'
                    f'<span class="rc-rank {_rank_class(i)}">{i + 1:02d}</span>'
                    f'{chip}</div>'
                    f'<div class="rc-score-row">{bar}'
                    f'<small>{score:.3f}{dist_txt}</small></div>',
                    unsafe_allow_html=True,
                )
                if on_similar:
                    st.button(
                        "Images similaires →", key=f"{key}-sim-{i}",
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
    page_head(
        "TBIR · CBIR",
        "Moteur de recherche d'images",
        "Recherche par mots-clés et par similarité visuelle sur Elasticsearch. "
        "Descripteurs MPEG-7 et descripteurs classiques (couleur, LBP, HOG), "
        "partition métrique de l'espace des index par VP-Tree, fusion rang-réciproque "
        "des deux modalités.",
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

    # ---- Bandeau de chiffres : cartes avec liseré d'accent --------------
    stat_items = [
        ("Elasticsearch", str(health["elasticsearch"]), "nœud"),
        ("Images visuelles", f"{stats['models'].get('inception_lbp', {}).get('images', 0):,}", "indexées"),
        ("Classes", str(len(classes)), "catégories"),
        ("Documents texte", f"{stats['text_documents']:,}", "BM25"),
    ]
    cols = st.columns(4, gap="small")
    for col, (lbl, val, unit) in zip(cols, stat_items):
        col.markdown(
            f'<div class="stat-card">'
            f'<div class="label">{lbl}</div>'
            f'<div class="value">{val}<span class="unit">{unit}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ---- Approches comparées : cartes narratives ------------------------
    st.markdown(
        '<div class="rule-ornament"><span>&#10038;&nbsp; Approches comparées</span></div>',
        unsafe_allow_html=True,
    )
    model_list = list(get_models().items())
    cols = st.columns(len(model_list), gap="medium")
    for i, (col, (name, cfg)) in enumerate(zip(cols, model_list)):
        n_images = stats["models"].get(name, {}).get("images", 0)
        col.markdown(
            f'<div class="approach">'
            f'<div class="idx">— N° {i + 1:02d}</div>'
            f'<h4>{cfg["label"]}</h4>'
            f'<div class="desc">{cfg.get("description", "")}</div>'
            f'<div class="meta">'
            f'<span>Vecteur <b>{cfg["dims"]}</b> dims</span>'
            f'<span>Images <b>{n_images:,}</b></span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # ---- Répartition de la base ----------------------------------------
    if classes:
        st.markdown(
            '<div class="rule-ornament"><span>&#10038;&nbsp; Répartition de la base</span></div>',
            unsafe_allow_html=True,
        )
        df = pd.DataFrame({"Classe": list(classes), "Images": list(classes.values())})
        chart = (
            alt.Chart(df)
            .mark_bar(size=28, cornerRadiusEnd=2)
            .encode(
                x=alt.X("Classe:N", sort="-y", title=None,
                        axis=alt.Axis(labelAngle=0, labelColor="#3c3c42",
                                      labelFont="Fraunces", labelFontSize=12,
                                      domainOpacity=0, tickOpacity=0)),
                y=alt.Y("Images:Q", title=None,
                        axis=alt.Axis(labelColor="#74737a", gridColor="#f1ede4",
                                      labelFont="JetBrains Mono", labelFontSize=10,
                                      domainOpacity=0, tickOpacity=0)),
                color=alt.value("#16161a"),
                tooltip=["Classe", "Images"],
            )
            .properties(height=240, background="transparent")
            .configure_view(strokeWidth=0)
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
    page_head(
        "TBIR",
        "Recherche textuelle",
        "Multi-champs sur titre (×3), tags (×2) et description, avec tolérance aux fautes.",
    )

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
                # Base locale (synthétique) → /images/<path>, sinon URL Flickr
                img_src = (f"{API_URL}/images/{r['image_path']}"
                           if r.get("image_path") else r.get("url", ""))
                try:
                    st.image(img_src, use_container_width=True)
                except Exception:
                    st.caption(img_src)
                rank_cls = _rank_class(i)
                score_norm = min(1.0, r["score"] / max(data["results"][0]["score"], 1e-6))
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:.5rem;'
                    f'margin-top:.4rem;">'
                    f'<span class="rc-rank {rank_cls}">{i + 1}</span>'
                    f'<strong style="line-height:1.2">{r.get("title") or "Sans titre"}</strong>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                hl = r.get("highlight", {})
                snippet = (hl.get("description") or hl.get("tags") or [""])[0]
                if snippet:
                    st.caption("…" + snippet + "…")
                st.markdown(_tag_pills(r.get("tags", "")), unsafe_allow_html=True)
                st.markdown(
                    f'<div class="rc-score-row">{_score_bar(score_norm, warm=True)}'
                    f'<small>BM25&nbsp;{r["score"]:.2f}</small></div>',
                    unsafe_allow_html=True,
                )


def page_image_search():
    page_head(
        "CBIR",
        "Recherche par image",
        "Donner une image en entrée — tirée de la base, uploadée ou pointée par une URL — "
        "et retrouver les plus proches dans l'espace du descripteur choisi.",
    )

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
    page_head(
        "Évaluation",
        "InceptionV3 + LBP contre VGG16",
        "La même requête visuelle est envoyée aux deux modèles, puis les métriques "
        "d'évaluation (précision@k, mAP, P@1) sont calculées sur l'ensemble de la base.",
    )
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
    page_head("Documentation", "À propos de ce projet")
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
# Descripteurs classiques + VP-Tree
# ======================================================================

@st.cache_data(ttl=120)
def get_descriptors():
    try:
        return api("GET", "/descriptors")
    except Exception:
        return {"available": [], "descriptors": {}, "all": {}}


def page_descriptor_search():
    page_head(
        "Descripteurs classiques",
        "Choix du descripteur, choix de l'index",
        "Couleur HSV, LBP, HOG — un ou plusieurs à la fois, avec des poids ajustables. "
        "La recherche k-NN passe par un VP-Tree (partition métrique de l'espace des index) "
        "ou, pour comparer, un scan linéaire exhaustif.",
    )

    desc = get_descriptors()
    if not desc["available"]:
        st.warning("Aucun index de descripteurs n'est encore construit. "
                   "Exécutez `scripts/build_descriptors.py` dans le conteneur backend.")
        return

    st.subheader("1. Choix des descripteurs")
    cols = st.columns(len(desc["available"]))
    chosen, weights = [], []
    for col, name in zip(cols, desc["available"]):
        meta = desc["descriptors"][name]
        with col.container(border=True):
            enable = st.checkbox(meta["label"], value=(name == "color"), key=f"desc-{name}")
            st.caption(meta["description"])
            w = st.slider("Poids", 0.0, 2.0, 1.0, 0.1, key=f"w-{name}",
                          disabled=not enable)
            if enable:
                chosen.append(name)
                weights.append(w)
    if not chosen:
        st.info("Cochez au moins un descripteur.")
        return

    st.subheader("2. Image requête")
    q_kind, q_val, q_class = query_picker("desc-pick")
    size = st.slider("Nombre de résultats", 1, 50, 10, key="desc-size")
    exact = st.toggle("Recherche exacte (linéaire, référence)", value=False,
                      key="desc-exact",
                      help="Désactivée → VP-Tree avec élagage métrique.")
    if not q_val:
        return
    if not st.button("Rechercher", type="primary", key="desc-go"):
        return

    extra = {"descriptors": ",".join(chosen),
             "weights": ",".join(str(w) for w in weights),
             "size": size, "exact": "1" if exact else "0"}
    with st.spinner("Recherche en cours..."):
        data = api("POST", "/search/descriptor", **request_kwargs(q_kind, q_val, extra))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Résultats", data["count"])
    c2.metric("Extraction", f"{data.get('extract_ms', 0):.0f} ms")
    c3.metric("Recherche", f"{data['search_ms']:.0f} ms")
    c4.metric("Index visité",
              f"{data.get('candidates', 0)} points"
              + (f"  (élagué {data['pruned_pct']:.1f} %)"
                 if "pruned_pct" in data and data["pruned_pct"] >= 0 else ""))

    image_results_grid(data["results"], query_class=q_class, key="desc-grid",
                       on_similar=None)


def page_combined_search():
    page_head(
        "Multi-modal",
        "Requête combinée",
        "Mots-clés et/ou image dans la même requête. Les deux listes de résultats "
        "sont fusionnées par rang-réciproque — robuste aux échelles différentes "
        "entre BM25 et distance L1.",
    )

    desc = get_descriptors()
    c1, c2 = st.columns([3, 2])
    with c1:
        query = st.text_input("Mots-clés (facultatif)", placeholder="ex : rose pink")
    with c2:
        size = st.number_input("Résultats", 1, 100, 10)

    use_image = st.toggle("Combiner avec une image", value=True)
    chosen, weights = [], []
    q_kind = q_val = q_class = None
    if use_image:
        if not desc["available"]:
            st.warning("Pas d'index descripteurs disponible.")
            use_image = False
        else:
            opt = st.multiselect(
                "Descripteurs visuels",
                options=desc["available"],
                default=desc["available"][:1],
                format_func=lambda n: desc["descriptors"][n]["label"],
            )
            chosen = opt
            weights = [1.0] * len(opt)
            q_kind, q_val, q_class = query_picker("combined-pick")

    if not st.button("Rechercher", type="primary", key="combined-go"):
        return
    if not query.strip() and not (use_image and q_val):
        st.warning("Fournissez un texte et/ou une image.")
        return

    extra = {"size": size}
    if query.strip():
        extra["q"] = query.strip()
    if use_image and q_val and chosen:
        extra["descriptors"] = ",".join(chosen)
        extra["weights"] = ",".join(str(w) for w in weights)
        kwargs = request_kwargs(q_kind, q_val, extra)
    else:
        kwargs = {"json": extra}

    with st.spinner("Recherche en cours..."):
        data = api("POST", "/search/combined", **kwargs)

    c1, c2, c3 = st.columns(3)
    c1.metric("Résultats", data["count"])
    if "text_ms" in data:
        c2.metric("Texte", f"{data['text_ms']:.0f} ms")
    if "visual_ms" in data:
        c3.metric("Visuel", f"{data['visual_ms']:.0f} ms")

    rrf_max = max((r.get("rrf_score") or 0.0) for r in data["results"]) or 1.0
    for i, r in enumerate(data["results"]):
        with st.container(border=True):
            c1, c2 = st.columns([1, 3.4])
            with c1:
                try:
                    st.image(f"{API_URL}/images/{r['image_path']}", use_container_width=True)
                except Exception:
                    pass
            with c2:
                rank_cls = _rank_class(i)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:.5rem;">'
                    f'<span class="rc-rank {rank_cls}">{i + 1}</span>'
                    f'<strong>{r.get("title") or r["image_path"]}</strong>'
                    f'<span class="rc-chip neutral">{r.get("class_name", "")}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="rc-score-row">{_score_bar(r["rrf_score"] / rrf_max)}'
                    f'<small>RRF&nbsp;{r["rrf_score"]:.4f}</small></div>',
                    unsafe_allow_html=True,
                )
                parts = []
                if r.get("text_score") is not None:
                    parts.append(f"<small>📝 BM25 <b>{r['text_score']:.2f}</b></small>")
                if r.get("visual_distance") is not None:
                    parts.append(f"<small>🎨 dist <b>{r['visual_distance']:.4f}</b></small>")
                if parts:
                    st.markdown(
                        f'<div style="display:flex;gap:1rem;color:var(--muted);'
                        f'margin-top:.3rem;">{"".join(parts)}</div>',
                        unsafe_allow_html=True,
                    )
                if r.get("tags"):
                    st.markdown(_tag_pills(r["tags"], limit=8), unsafe_allow_html=True)


# ======================================================================
# Page MIRFLICKR-1M
# ======================================================================

@st.cache_data(ttl=60)
def mirflickr_stats():
    try:
        return api("GET", "/mirflickr/stats")
    except Exception:
        return {"indexed_documents": 0, "mpeg7_descriptors": [], "has_text": False}


def page_mirflickr():
    page_head(
        "Benchmark 1M",
        "MIRFLICKR-1M",
        "Un million d'images Flickr livrées avec deux descripteurs MPEG-7 pré-calculés : "
        "Edge Histogram (150 dims) et Homogeneous Texture (43 dims).",
    )

    s = mirflickr_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Documents indexés", f"{s['indexed_documents']:,}")
    c2.metric("Descripteurs MPEG-7", ", ".join(s["mpeg7_descriptors"]) or "—")
    c3.metric("État", "prêt" if s["has_text"] else "non indexé")
    if not s["has_text"]:
        st.info("Exécutez `scripts/index_mirflickr.py` dans le conteneur backend.")
        return

    tab1, tab2 = st.tabs(["Recherche textuelle", "Similarité MPEG-7"])
    with tab1:
        with st.form("mir-text"):
            c1, c2 = st.columns([4, 1])
            q = c1.text_input("Mots-clés", placeholder="ex : sunset beach",
                              label_visibility="collapsed")
            size = c2.number_input("Résultats", 1, 50, 12,
                                   label_visibility="collapsed")
            go = st.form_submit_button("Rechercher", type="primary")
        if go and q.strip():
            d = api("GET", "/mirflickr/search", params={"q": q, "size": size})
            st.success(f"{d['total']:,} résultats, {d['search_ms']:.0f} ms")
            s_max = max(r["score"] for r in d["results"]) or 1.0
            cols = st.columns(4)
            for i, r in enumerate(d["results"]):
                with cols[i % 4].container(border=True):
                    rank_cls = _rank_class(i)
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:.5rem;">'
                        f'<span class="rc-rank {rank_cls}">{i + 1}</span>'
                        f'<strong style="line-height:1.2">'
                        f'{r["title"] or "Sans titre"}</strong></div>'
                        f'<div style="color:var(--muted);font-size:.78rem;margin-top:.3rem;">'
                        f'ID <code>{r["photo_id"]}</code> · '
                        f'<em>{r["owner"] or "inconnu"}</em></div>'
                        f'<div class="rc-score-row">'
                        f'{_score_bar(r["score"] / s_max, warm=True)}'
                        f'<small>BM25&nbsp;{r["score"]:.2f}</small></div>'
                        f'<div style="margin-top:.3rem;">'
                        f'{_tag_pills(r.get("tags",""), limit=6)}</div>'
                        + (f'<div style="color:var(--muted);font-size:.68rem;'
                           f'margin-top:.4rem;">⚖ {r["license"]}</div>'
                           if r.get("license") else ""),
                        unsafe_allow_html=True,
                    )

    with tab2:
        c1, c2, c3 = st.columns([2, 2, 1])
        pid = c1.number_input("photo_id MIRFLICKR", 0, 999_999, 10, step=1)
        name = c2.selectbox(
            "Descripteur",
            s["mpeg7_descriptors"],
            format_func=lambda n: ({"edge": "Edge Histogram (MPEG-7)",
                                    "homo": "Homogeneous Texture (MPEG-7)"}
                                   .get(n, n)),
        )
        size = c3.number_input("Résultats", 1, 50, 10)
        if st.button("Rechercher voisins", type="primary", key="mir-sim"):
            d = api("GET", "/mirflickr/similar", timeout=120,
                    params={"photo_id": pid, "descriptor": name, "size": size})
            index_tag = (f"VP-Tree (élagué {d['pruned_pct']:.1f} %)"
                         if d.get("index") == "vptree"
                         else "scan linéaire exhaustif")
            st.success(f"{d['count']} résultats, {d['search_ms']:.0f} ms — {index_tag}")
            # Distances L1 : plus petit = plus proche. Barre inversée.
            d_max = max(r["distance"] for r in d["results"]) or 1.0
            cols = st.columns(4)
            for i, r in enumerate(d["results"]):
                with cols[i % 4].container(border=True):
                    rank_cls = _rank_class(i)
                    sim = 1.0 - min(1.0, r["distance"] / d_max)
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:.5rem;">'
                        f'<span class="rc-rank {rank_cls}">{i + 1}</span>'
                        f'<strong style="line-height:1.2">'
                        f'{r.get("title") or "Sans titre"}</strong></div>'
                        f'<div style="color:var(--muted);font-size:.78rem;margin-top:.3rem;">'
                        f'ID <code>{r["photo_id"]}</code></div>'
                        f'<div class="rc-score-row">{_score_bar(sim)}'
                        f'<small>dist&nbsp;L1&nbsp;{r["distance"]:.3f}</small></div>'
                        f'<div style="margin-top:.3rem;">'
                        f'{_tag_pills(r.get("tags",""), limit=6)}</div>',
                        unsafe_allow_html=True,
                    )


# ======================================================================
# Navigation
# ======================================================================

pages = st.navigation([
    st.Page(page_home, title="Accueil", icon="🏠", default=True),
    st.Page(page_text_search, title="Recherche textuelle", icon="📝", url_path="texte"),
    st.Page(page_image_search, title="Recherche par image", icon="🖼️", url_path="image"),
    st.Page(page_descriptor_search, title="Descripteurs + VP-Tree", icon="🎨",
            url_path="descripteurs"),
    st.Page(page_combined_search, title="Requête combinée", icon="🔗",
            url_path="combinee"),
    st.Page(page_mirflickr, title="MIRFLICKR-1M", icon="🌐",
            url_path="mirflickr"),
    st.Page(page_compare, title="Comparaison des modèles", icon="⚖️", url_path="comparaison"),
    st.Page(page_about, title="À propos", icon="ℹ️", url_path="a-propos"),
])
pages.run()
