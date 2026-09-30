# Dockerfile for Streaming Live RAG Engine
# Meets Gate G1: Single-command container launch with automated replay

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download default sentence-transformers model to ensure offline execution in container
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application source code, corpora, benchmarks, and tests
COPY streaming_rag/ ./streaming_rag/
COPY data/ ./data/
COPY evaluation/ ./evaluation/
COPY tests/ ./tests/
COPY cli.py .
COPY pyproject.toml .

# Environment settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command launches the automated benchmark replay suite (Gate G1)
CMD ["python", "-m", "evaluation.benchmark_runner"]
