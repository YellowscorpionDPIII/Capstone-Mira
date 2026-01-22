# Production-ready Dockerfile for Mira platform
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt setup.py README.md ./
COPY mira/__init__.py mira/__init__.py

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install package in editable mode
RUN pip install -e .

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 mira && \
    chown -R mira:mira /app

USER mira

# Expose webhook port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')" || exit 1

# Run the application
CMD ["python", "-m", "mira.app"]
