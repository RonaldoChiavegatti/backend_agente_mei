# Frontend Agente MEI

SPA construída com React + Vite + Tailwind para consumir os serviços do backend Agente MEI.

## Requisitos

- Node.js 18+
- pnpm, npm ou yarn

## Configuração

```bash
cp .env.example .env
# ajuste VITE_API_BASE_URL para o domínio/porta do proxy reverso (ex.: http://localhost:8080/api)
npm install
npm run dev
```

## Rodando via Docker

1. Garanta que o `.env` na raiz do repositório tenha `FRONTEND_HOST_PORT` e `VITE_API_BASE_URL` configurados (os valores padrão já apontam para `http://localhost:8080/api`).
2. Construa e suba os containers normalmente:

```bash
docker-compose up --build frontend
```

3. O diretório `./frontend` é montado dentro do container, então salvar arquivos localmente dispara o hot reload do Vite.
4. Acesse o SPA em `http://localhost:<FRONTEND_HOST_PORT>` (por padrão, `http://localhost:5173`).
5. As requisições continuarão apontando para o Gateway exposto pelo Nginx (`VITE_API_BASE_URL`).

Principais rotas:

- `/login` e `/register`
- `/dashboard`
- `/documents`
- `/agent`
- `/billing`
