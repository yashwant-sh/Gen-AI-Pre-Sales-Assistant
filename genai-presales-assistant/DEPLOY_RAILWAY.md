# Deploy on Railway

This repo has **two** deployable targets: **API** (Dockerfile) and **Streamlit UI** (Dockerfile.frontend). Railway runs them as **two services** that share the same GitHub repo.

## Prerequisites

1. [Railway](https://railway.app) account and **GitHub** repo pushed (already done for yours).
2. **Groq** (default LLM): create a secret `GROQ_API_KEY` on the API service (from `.env.example`).

## Step 1 — Deploy the API

1. Railway → **New Project** → **Deploy from GitHub** → pick `genai-presales-assistant`.
2. When the service is created, open **Settings**:
   - **Dockerfile Path:** `Dockerfile`
   - (Leave root directory blank / repo root.)
3. **Variables** (example):

   | Name | Value |
   |------|--------|
   | `GROQ_API_KEY` | your key |
   | `DEFAULT_LLM_PROVIDER` | `groq` |

   Optional overrides: `DATABASE_PATH`, `DOCUMENTS_PATH`, `VECTOR_STORE_PATH` (defaults work for ephemeral disk).

4. **Deploy** and wait until the build finishes. First boot downloads the embedding model and may take **several minutes** if the hobby CPU is slow.
5. Generate a **public domain**: **Settings → Networking → Generate Domain**. Copy the URL, e.g. `https://your-api-production.up.railway.app`.

## Step 2 — Deploy the Streamlit frontend

1. In the **same Railway project**, **New Service** → **GitHub** → **same repo** again.
2. **Settings**:
   - **Dockerfile Path:** `Dockerfile.frontend`
3. **Variables**:

   | Name | Value |
   |------|--------|
   | `BACKEND_URL` | exact API URL from step 1 (**https**, **no** trailing slash) |

4. Deploy and assign a **public domain** for the UI (Settings → Networking).

Open the Streamlit URL in a browser; the footer should show your `BACKEND_URL`.

## Troubleshooting

- **503 / crash on boot:** Increase memory tier or retry; embedding + Torch can need **≥1 GB RAM** on cold start.
- **UI shows “cannot connect”:** Wrong `BACKEND_URL`, or API not healthy. Check API logs and `GET /health` on the API domain.
- **SQLite / FAISS lost on redeploy:** Ephemeral filesystem. Add a [Railway volume](https://docs.railway.app/guides/volumes) and point `DATABASE_PATH` / `VECTOR_STORE_PATH` at mounted paths.

## Single-service option

If you only need the REST API for demos: deploy **Dockerfile** only and use Swagger at `https://<api>/docs` (no frontend service).
