# Multi-stage build for NeuroSonix backend

# Stage 1: Dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies.
# Pin setuptools < 81 for the build: the openai-whisper sdist's setup.py imports
# pkg_resources, which setuptools >= 81 no longer ships. PIP_CONSTRAINT reaches
# pip's isolated build environment so the wheel build finds pkg_resources.
RUN echo "setuptools<81" > /tmp/constraints.txt && \
    PIP_CONSTRAINT=/tmp/constraints.txt pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Set PATH
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY . .

# Create upload and annotation directories
RUN mkdir -p uploads annotations

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "main.py"]
