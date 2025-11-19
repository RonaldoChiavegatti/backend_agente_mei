# Build image for the Vite dev server so the SPA can run via Docker Compose
FROM node:20-alpine

ARG APP_VERSION=dev
LABEL org.opencontainers.image.title="frontend" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.description="Vite dev server for Agente MEI"
ENV APP_VERSION=$APP_VERSION

WORKDIR /app

# Install dependencies first to leverage Docker cache
COPY package*.json ./
RUN npm install

# Copy the rest of the source code
COPY . .

EXPOSE 5173
ENV HOST=0.0.0.0
ENV PORT=5173

CMD ["sh", "-c", "npm run dev -- --host $HOST --port $PORT"]
