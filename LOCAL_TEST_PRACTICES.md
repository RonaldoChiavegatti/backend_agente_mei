# Boas práticas para testar frontend e backend localmente

## Preparação rápida
- **Backend**: copie `.env.example` para `.env` na raiz e preencha Postgres, Mongo, Redis, storage, `GEMINI_API_KEY`, `JWT_SECRET_KEY` e `NGINX_HOST_PORT` (padrão `8080`).
- **Frontend**: copie `frontend/.env.example` para `frontend/.env` e defina `VITE_API_BASE_URL=http://localhost:8080/api` (ou o host/porta que você expõe do gateway).
- **Subida dos serviços**: execute `docker-compose up --build` na raiz para iniciar Postgres, Mongo, Redis, serviços internos e o gateway Nginx que publica tudo sob `/api`.

## Roteamento e chamadas
- Aponte todas as requisições do frontend para o gateway (`http://localhost:8080/api`). Ele já roteia para `auth`, `documents`, `agent` e `billing` preservando o prefixo `/api`.
- Mantenha o header `Authorization: Bearer <token>` após login para exercitar o fluxo real de autenticação.

## Fluxos de teste recomendados
- **Happy path de autenticação**: `POST /auth/register` → `POST /auth/login` → reaproveite o `access_token` em chamadas subsequentes.
- **Uploads e jobs de documentos**: `POST /documents/upload` com `multipart/form-data` → consulte `GET /documents/jobs/{job_id}` e `GET /documents/jobs` para validar polling e estados assíncronos.
- **Conversas com agentes**: `POST /chat` enviando `agent_id`, `user_message` e `conversation_history` para checar serialização e autorização.
- **Faturamento exposto**: `GET /billing/balance/{user_id}` e `GET /billing/transactions/{user_id}` usando o ID do usuário autenticado para garantir aderência às permissões.

## Dicas para produtividade
- **Scripts de fumaça**: mantenha um pequeno script (curl, HTTP client ou Playwright) que faça register → login → profile → upload (com polling) → chat para detectar regressões rápidas.
- **Checagem de saúde inicial**: antes dos testes, confirme que os containers estão de pé na porta esperada (`docker-compose up --build` já abre tudo) para evitar erros de conexão intermitentes.
- **Logs lado a lado**: deixe o console do gateway e serviços aberto enquanto roda o frontend para correlacionar CORS, JWT expirado ou paths incorretos.
- **Dados descartáveis**: use contas/arquivos de teste descartáveis para repetir cenários sem limpeza manual de banco.
