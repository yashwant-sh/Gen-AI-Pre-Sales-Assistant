# FastAPI backend (Railway deploy: set Root Directory repo root; Dockerfile path Dockerfile)
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Railway injects PORT; local fallback 8001 matches frontend.py default
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
