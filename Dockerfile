# Service 1: Document Text Extraction - Standalone Dockerfile
# ============================================================
# This Dockerfile is for the distribution package.
# It expects to be built from the package root directory.

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy configuration




# Copy all files (backend/, aithon_imports.py, project_root.py, start_api.py)
COPY backend/ ./backend/
COPY .envvar-service1 ./backend/.envvar-service1
COPY .envvar-service1 ./backend/.envvar


COPY aithon_imports.py ./
COPY project_root.py ./
COPY start_api.py ./

# Create necessary directories
RUN mkdir -p /app/output /app/logs /app/datalake

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8015

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8015/api/document-text-extraction/health || exit 1

# Start Service 1 API server
WORKDIR /app
CMD ["python", "start_api.py"]

