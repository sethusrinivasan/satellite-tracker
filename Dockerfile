FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for C/C++ model extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

# Ensure instance and data directories exist
RUN mkdir -p instance app/models data

EXPOSE 5000

ENV PORT=5000
ENV FLASK_ENV=production
ENV RUNNING_IN_DOCKER=true

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
  CMD curl -fsS http://127.0.0.1:5000/health || exit 1

CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120"]
