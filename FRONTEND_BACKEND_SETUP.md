# Guia rápido para integrar frontend e backend

Este guia explica como preparar as variáveis de ambiente, subir os serviços com Docker e apontar o frontend para o API Gateway.

## Pré-requisitos
- Docker e Docker Compose instalados.
- Uma cópia do repositório clonada localmente.

## 1. Configure o arquivo `.env`
1. Duplique o exemplo fornecido e ajuste os valores necessários:
   ```bash
   cp .env.example .env
   ```
2. Edite o `.env` com os valores do seu ambiente. Os campos a seguir são os principais para rodar localmente:
   - **Banco de dados**: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`
   - **Mongo**: `MONGO_URL`, `MONGO_DB`
   - **Redis**: `REDIS_URL`
   - **Autenticação**: `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
   - **Armazenamento S3 (Oracle)**: `ORACLE_ENDPOINT`, `ORACLE_ACCESS_KEY_ID`, `ORACLE_SECRET_ACCESS_KEY`, `ORACLE_BUCKET`
   - **LLM**: `GEMINI_API_KEY`
   - **Porta do Gateway**: `NGINX_HOST_PORT` (padrão `8080` para expor o Nginx)
   - **Frontend**: `FRONTEND_HOST_PORT` (porta usada para expor o Vite dev server) e `VITE_API_BASE_URL` (URL do Gateway consumida pelo SPA)

> Dica: para um ambiente de desenvolvimento local, você pode manter os valores padrão do exemplo e apenas alterar os segredos (`JWT_SECRET_KEY`, chaves S3 e `GEMINI_API_KEY`).

## 2. Suba os serviços
Na raiz do projeto, construa e inicie todos os containers:
```bash
docker-compose up --build
```

Os serviços principais ficarão disponíveis via API Gateway em `http://localhost:<NGINX_HOST_PORT>/api` (por padrão, `http://localhost:8080/api`).

## 3. Rode o frontend via Docker
- O `docker-compose up --build` agora cria também o container `frontend`, exposto em `http://localhost:<FRONTEND_HOST_PORT>` (por padrão, `http://localhost:5173`).
- As variáveis `HOST`/`PORT` são configuradas automaticamente para que o Vite dev server rode dentro do container.
- Ajuste `VITE_API_BASE_URL` no `.env` raiz, caso o Gateway esteja em outra porta/domínio.
- O diretório `./frontend` é montado dentro do container, então qualquer alteração local dispara hot reload do Vite.

## 4. Aponte o frontend para o backend
- Configure a base URL do frontend para o Gateway: `http://localhost:<NGINX_HOST_PORT>/api`.
- Use os endpoints documentados em `backend/FRONTEND_INTEGRATION.md`.
- Para rotas protegidas, obtenha um token via `POST /auth/login` e envie `Authorization: Bearer <token>` em cada requisição.

## 5. Teste o fluxo básico
1. Registre um usuário com `POST /auth/register`.
2. Faça login com `POST /auth/login` e copie o `access_token`.
3. Use o token para acessar rotas autenticadas (por exemplo, `GET /auth/profile`).

Seguindo esses passos, o frontend já conseguirá consumir o backend com as variáveis de ambiente corretas e os serviços em execução.
