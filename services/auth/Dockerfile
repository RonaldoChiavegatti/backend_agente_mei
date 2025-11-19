FROM python:3.11-slim

ARG APP_VERSION=dev
LABEL org.opencontainers.image.title="auth-service" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.description="FastAPI authentication service for Agente MEI"
ENV APP_VERSION=$APP_VERSION

WORKDIR /app

RUN apt-get update \
    && apt-get install -y build-essential python3.11-distutils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
