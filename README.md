# Backend Agente MEI

Este repositório concentra o backend, o frontend e toda a infraestrutura em Docker do Agente MEI, um conjunto de microserviços em Python/FastAPI voltados a automatizar tarefas de MEIs (cadastro, orquestração de agentes de IA, upload e processamento de documentos, bilhetagem etc.).

## Como navegar pela estrutura

| Caminho | Conteúdo |
| --- | --- |
| `backend/` | Código compartilhado dos serviços FastAPI, utilitários e documentação técnica específica (por exemplo, `backend/ARCHITECTURE.md` e `backend/FRONTEND_INTEGRATION.md`). |
| `services/` | Implementações isoladas dos microserviços (auth, billing, documents, agent, worker) usados no `docker-compose.yml`. |
| `frontend/` | SPA em Vite/React preparada para ser servida junto com o backend via Docker. |
| `docker-compose.yml` | Orquestração completa dos containers (Postgres, Mongo, Redis, microserviços, worker, frontend e Nginx). |
| `nginx/` | Configuração do API Gateway responsável por expor as rotas externas como `/api/*`. |
| `scripts/` | Utilitários de manutenção (por exemplo, backups descritos em `DEPLOYMENT.md`). |

### Documentações úteis

- [`backend/README.md`](backend/README.md): visão geral dos serviços e como cada um se conecta.
- [`backend/ARCHITECTURE.md`](backend/ARCHITECTURE.md): detalhes da arquitetura de microserviços.
- [`backend/FRONTEND_INTEGRATION.md`](backend/FRONTEND_INTEGRATION.md): endpoints e fluxo para o frontend.
- [`FRONTEND_BACKEND_SETUP.md`](FRONTEND_BACKEND_SETUP.md): passo a passo para subir backend+frontend com Docker.
- [`DEPLOYMENT.md`](DEPLOYMENT.md): guia completo de publicação em uma VM (útil como referência de infraestrutura).
- [`LOCAL_TEST_PRACTICES.md`](LOCAL_TEST_PRACTICES.md): práticas recomendadas para testes locais.

> Dica: use `rg <palavra-chave>` na raiz do repositório para encontrar rapidamente onde cada funcionalidade foi documentada ou implementada.

## Requisitos para rodar localmente

1. **Distribuição Linux recente (Ubuntu 22.04+).**
2. **Docker e Docker Compose plugin.** Instale com:
   ```bash
   sudo apt update
   sudo apt install -y ca-certificates curl gnupg
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
     sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   sudo apt update
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   sudo usermod -aG docker $USER  # faça logout/login para aplicar
   ```
3. **Git** para clonar o projeto:
   ```bash
   sudo apt install -y git
   ```

## Configurando o ambiente (.env)

1. Copie o arquivo de exemplo na raiz:
   ```bash
   cp .env.example .env
   ```
2. Ajuste as variáveis principais:
   - **Banco de dados**: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`.
   - **Mongo / Redis**: `MONGO_URL`, `MONGO_DB`, `REDIS_URL`.
   - **Autenticação**: `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
   - **Armazenamento S3-compatível**: `ORACLE_ENDPOINT`, `ORACLE_ACCESS_KEY_ID`, `ORACLE_SECRET_ACCESS_KEY`, `ORACLE_BUCKET`.
   - **LLM**: `GEMINI_API_KEY`.
   - **Exposição de portas**: `NGINX_HOST_PORT` (gateway) e `FRONTEND_HOST_PORT`.
   - **Frontend**: `VITE_API_BASE_URL` apontando para `http://localhost:<NGINX_HOST_PORT>/api`.

Para gerar segredos fortes, utilize `openssl rand -hex 32`.

## Rodando o stack completo

1. **Clone o repositório e acesse a pasta raiz:**
   ```bash
   git clone https://github.com/<sua-organizacao>/backend_agente_mei.git
   cd backend_agente_mei
   ```
2. **Suba todos os serviços via Docker Compose:**
   ```bash
   docker compose up --build
   ```
   - O frontend ficará exposto em `http://localhost:${FRONTEND_HOST_PORT:-5173}`.
   - As APIs estarão disponíveis em `http://localhost:${NGINX_HOST_PORT:-8080}/api` (por exemplo, `/api/auth/health`).
3. **Verifique os logs se precisar depurar:**
   ```bash
   docker compose logs -f
   ```
4. **Executando em segundo plano:**
   ```bash
   docker compose up -d --build
   ```
5. **Encerrando os serviços:**
   ```bash
   docker compose down
   ```

## Testando o fluxo básico

1. Registre um usuário com `POST /api/auth/register`.
2. Faça login em `POST /api/auth/login` para obter o `access_token`.
3. Chame as rotas protegidas (ex.: `GET /api/auth/profile`) enviando `Authorization: Bearer <token>`.
4. Utilize `backend/FRONTEND_INTEGRATION.md` para conhecer os demais endpoints e fluxos de upload/documentos.

## Próximos passos

- Consulte `LOCAL_TEST_PRACTICES.md` para saber como exercitar cada serviço isoladamente.
- Veja `DEPLOYMENT.md` caso precise publicar em uma VM ou configurar backups.
- Abra os READMEs em `services/<nome-do-servico>/README.md` para detalhes específicos de cada microserviço.

Com isso você terá um guia único para localizar a documentação, configurar o ambiente Linux e executar o projeto completo para testes locais.
