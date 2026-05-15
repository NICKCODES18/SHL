FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Lightweight production image (no torch/chroma) — reliable for evaluators
COPY requirements-vercel.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY app/static ./app/static
COPY api ./api
COPY scripts/prebuild_tfidf.py ./scripts/prebuild_tfidf.py
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
COPY data/catalog.json ./data/catalog.json

RUN chmod +x /docker-entrypoint.sh

# Build search indices at image build time (bundled in image)
RUN python scripts/prebuild_tfidf.py

ENV PYTHONPATH=/app
ENV PORT=8000
ENV USE_LIGHT_RETRIEVAL=true
ENV VERCEL=1

EXPOSE 8000

# Render sets PORT dynamically — entrypoint reads $PORT
ENTRYPOINT ["/docker-entrypoint.sh"]
