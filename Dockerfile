# =============================================================================
# Dockerfile for kreat_rag (retrieval-optimized branch)
# FastAPI RAG service: parse → ingest → hybrid retrieval (BGE + FAISS + BM25)
# =============================================================================

# --- Stage 1: Base image ---
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# =============================================================================
# System dependencies
# =============================================================================
# build-essential  → needed to compile C extensions (faiss-cpu, numpy wheels)
# libgomp1         → OpenMP runtime required by faiss-cpu for parallel search
# curl             → useful for health checks inside the container
# We clean up apt cache immediately to keep the image layer small.
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Python dependencies
# =============================================================================
# Copy requirements first (before source code) so Docker can cache this layer.
# If only your .py files change, Docker reuses this cached pip-install layer
# and avoids re-downloading packages on every build.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Application source code
# =============================================================================
# Copy all project files into /app.
# .dockerignore (see companion file) should exclude: __pycache__, .git,
# local venvs, and any large data/ directories you don't want baked in.
COPY . .

# =============================================================================
# Runtime directories
# =============================================================================
# The app reads/writes FAISS indexes to data/faiss_index at runtime.
# Creating it here ensures the directory exists even before the first ingest.
RUN mkdir -p data/faiss_index

# =============================================================================
# Environment variables
# =============================================================================
# FAISS_INDEX_DIR  → where the app looks for / saves the FAISS index.
#                    Matches the default used in main.py lifespan hook.
# PYTHONUNBUFFERED → forces Python stdout/stderr to be unbuffered so logs
#                    appear in docker logs in real-time (no buffering surprises).
# PYTHONDONTWRITEBYTECODE → skip .pyc files; keeps container filesystem clean.
ENV FAISS_INDEX_DIR=data/faiss_index \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# =============================================================================
# Port
# =============================================================================
# The app is served by uvicorn on port 8000 (per main.py comments).
# EXPOSE documents this intent — it does NOT publish the port;
# that happens at `docker run -p 8000:8000` or in docker-compose.
EXPOSE 8000

# =============================================================================
# Health check
# =============================================================================
# Docker will periodically hit /health. If it returns non-200 three times in
# a row, the container is marked "unhealthy". Useful in compose / Kubernetes.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# =============================================================================
# Entrypoint
# =============================================================================
# We use uvicorn directly (no --reload in production).
# --host 0.0.0.0  → listen on all interfaces, not just localhost.
#                    Without this the app would be unreachable from outside
#                    the container even if the port is published.
# --port 8000     → matches EXPOSE above.
# --workers 1     → single worker is correct here because the BGE model +
#                    FAISS index are loaded once into the process via the
#                    lifespan singleton. Multiple workers would each load
#                    their own ~1.3 GB copy of BGE, multiplying RAM usage.
#                    Scale horizontally via container replicas instead.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]