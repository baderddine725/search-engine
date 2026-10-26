# Demo script — VisionSearch AI

Target length: 3–4 minutes. Everything is live at these URLs:

| URL                      | What it is                                   |
|--------------------------|-----------------------------------------------|
| http://localhost:3000    | **VisionSearch AI** (React web app) — primary |
| http://localhost:8501    | Streamlit interface (original, still works)   |
| http://localhost:5000    | Flask REST API                                |
| http://localhost:9200    | Elasticsearch                                 |

## 1 · Overview `/`
- Point at the hero gradient and the two prominent actions (**Search by Text / Search by Image**).
- Six stat cards: indexed images, text documents, categories, feature models, average
  latency and latest mAP — all live, no mock data.
- Service-health card: six rows (Flask, Elasticsearch, Elastiknn, InceptionV3+LBP, VGG16,
  MIRFLICKR-1M). All should be green.
- Dataset preview grid — click any thumbnail and it jumps straight to Similar Images.

## 2 · Text Search `/text`
Sample query to type: **`sunflower`**
- Hit Enter: the result grid fills with BM25-ranked matches.
- Highlighted keywords in snippets, category chips, BM25 bar.
- The **"Find visually similar →"** button on any card pivots to Visual Search for that image.

## 3 · Visual Search `/visual`
- Default source is **Dataset**. Pick any image on the left (e.g. a rose).
- Switch between InceptionV3 + LBP and VGG16 to show the model radio inline.
- Press **Run visual search →**. Results come back with distance / score and ranked numerals.
- Show the three input modes (Dataset / Upload / URL) by clicking through.

## 4 · Similar Images `/similar?path=…`
- Automatically opens from a result or dataset thumbnail click.
- Point out the **breadcrumb trail** at the top — click one of the earlier images to show
  iterative discovery.

## 5 · Model Comparison `/compare`
- Pick a dataset image, press **Compare**.
- Two side-by-side panels show the same query ranked by both models, with per-model
  precision, AP and latency.
- Below: a **precision-at-rank line chart** and a **metric bar chart** comparing the two.

## 6 · Evaluation `/evaluation`
- Shows the latest benchmark (regenerated above).
- Four blocks: headline metrics, precision-at-rank chart, per-class AP chart, and raw
  per-model data (mAP · P@1 · P@k · latency, both Exact and LSH).
- The **Run benchmark** button is wired (don't click during the demo — takes minutes).

## 7 · Architecture `/architecture`
- Flat SVG diagram of the whole stack with the three pipelines (text / visual / benchmark)
  laid out underneath.

## 8 · API Docs `/api`
- Scroll the left sidebar; click `/search/image` to show the full endpoint, params table,
  cURL request and response panel. Everything has a copy-to-clipboard button.

## 9 · Settings `/settings`
- One-click **light ↔ dark** toggle. Persisted. Great visual contrast for the recording.
- Shows the Flask base URL (`http://localhost:5000`).

## Pre-flight checklist
Before recording:
```bash
docker compose ps                        # all four containers Up
curl http://localhost:5000/health        # ok
curl http://localhost:5000/stats         # 400 images, 400 docs, 5 classes
curl http://localhost:5000/mirflickr/stats  # 1,000,000 docs
```
Hard-refresh the browser (Ctrl + Shift + R) to pick up the fresh Tailwind bundle.
