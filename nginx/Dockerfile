FROM nginx:stable

ARG APP_VERSION=dev
LABEL org.opencontainers.image.title="nginx-gateway" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.description="API gateway and static proxy for Agente MEI"
ENV APP_VERSION=$APP_VERSION

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY nginx.conf /etc/nginx/nginx.conf

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://localhost/healthz || exit 1
