# ============================================================
# Dockerfile – News Alpha Engine
# ============================================================

FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ libpq-dev curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY . .

# Create directories
RUN mkdir -p data/raw data/processed data/reports logs

# Non-root user
RUN useradd -m -u 1000 newsalpha && chown -R newsalpha:newsalpha /app
USER newsalpha

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py", "server"]
