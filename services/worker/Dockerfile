FROM python:3.11-slim

ARG APP_VERSION=dev
LABEL org.opencontainers.image.title="worker-service" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.description="Background worker for document processing"
ENV APP_VERSION=$APP_VERSION

WORKDIR /app

RUN apt-get update \
    && apt-get install -y build-essential python3-distutils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["celery", "-A", "app.tasks", "worker", "--loglevel=info"]
