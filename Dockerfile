FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Lightweight production image (no torch/chroma) — reliable for evaluators
COPY requirements-vercel.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY api ./api
COPY scripts/prebuild_tfidf.py ./scripts/prebuild_tfidf.py
COPY data/catalog.json ./data/catalog.json

# Build search indices at image build time (bundled in image)
RUN python scripts/prebuild_tfidf.py

ENV PYTHONPATH=/app
ENV PORT=8000
ENV USE_LIGHT_RETRIEVAL=true
ENV VERCEL=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
