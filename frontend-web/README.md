# VisionSearch AI — Web Frontend

A standalone React + TypeScript + Vite + Tailwind frontend for the image
search backend. Lives next to the original Streamlit interface (`frontend/`)
and talks to the same Flask API (`backend/`).

## Pages

| Route            | What it does                                                     |
|------------------|------------------------------------------------------------------|
| `/`              | Overview — hero search bar, live stats, service health, dataset preview |
| `/text`          | Semantic text search (BM25) with highlighted matches             |
| `/visual`        | Visual search by upload / URL / dataset pick, with a model selector |
| `/similar`       | Iterative similarity exploration with breadcrumb history         |
| `/compare`       | Side-by-side model comparison with charts                        |
| `/dataset`       | Paginated dataset explorer with filters                          |
| `/evaluation`    | Benchmark dashboard with mAP / P@1 charts; can trigger a new run |
| `/architecture`  | SVG system diagram + pipeline walkthroughs                       |
| `/api`           | API reference with copy-to-clipboard examples                    |
| `/settings`      | Theme toggle, backend URL display, local cache control           |

## Running

### With Docker (recommended)

```bash
docker compose up -d --build frontend-web
# http://localhost:3000
```

### Local development

```bash
cd frontend-web
npm install
VITE_API_BASE_URL=http://localhost:5000 npm run dev
# http://localhost:5173
```

The backend must have CORS enabled (`flask-cors`) when the two run on
different origins — it is enabled by default in `backend/app.py`.

## Configuration

| Variable              | Where            | Default                 |
|-----------------------|------------------|-------------------------|
| `VITE_API_BASE_URL`   | build-time env   | `http://localhost:5000` |

For production, build with the real backend URL baked in:

```bash
docker compose build --build-arg VITE_API_BASE_URL=https://api.example.com frontend-web
```

## Stack

React 18, TypeScript, Vite 5, Tailwind 3, Recharts, Lucide icons, React Router 6.
