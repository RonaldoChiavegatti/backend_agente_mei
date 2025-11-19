# Deploy em Servidor Remoto

Este guia descreve como publicar o MVP em uma VM na nuvem usando o mesmo `docker compose` do ambiente de desenvolvimento. Ao final do processo, todas as APIs ficarão acessíveis externamente através do NGINX.

## 1. Pré-requisitos da VM

- Máquina Linux (Ubuntu 22.04 ou similar) com pelo menos 4 vCPUs, 8 GB de RAM e 40 GB de disco.
- Acesso SSH com um usuário com privilégios de `sudo`.
- Porta pública liberada para HTTP (80) e, opcionalmente, HTTPS (443) no provedor de nuvem/firewall.
- (Opcional) Um domínio apontando para o IP público da VM.

## 2. Instalar Docker e Docker Compose

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Executar Docker sem sudo (requer logout/login)
sudo usermod -aG docker $USER
```

Faça logout/login para que seu usuário passe a pertencer ao grupo `docker`.

## 3. Obter o código do projeto

```bash
git clone https://github.com/<sua-organizacao>/backend_agente_mei.git
cd backend_agente_mei
```

Caso prefira copiar apenas os artefatos necessários, transfira para a VM o conteúdo desta pasta via `scp` ou outra ferramenta de deploy.

## 4. Configurar variáveis de ambiente

1. Copie o arquivo de exemplo:
   ```bash
   cp .env.example .env
   ```
2. Edite `.env` e substitua os valores conforme o ambiente de produção:
   - **Credenciais do Postgres/Mongo/Redis:** mantenha segredos fortes.
   - **Oracle Object Storage:** informe `ORACLE_ENDPOINT`, `ORACLE_ACCESS_KEY_ID`, `ORACLE_SECRET_ACCESS_KEY` e `ORACLE_BUCKET` usados para o armazenamento de documentos. Caso utilize outro provedor S3-compatível, ajuste o endpoint e chaves.
   - **GEMINI_API_KEY:** chave válida do provedor de LLM.
   - **JWT_SECRET_KEY:** gere um segredo aleatório.
- **ENVIRONMENT:** defina `prod` ou outro valor que represente o ambiente remoto.
- **NGINX_HOST_PORT:** defina `8080` para expor todo o tráfego HTTP via NGINX na própria VM. Caso use um load balancer terminando TLS, faça-o encaminhar para essa porta.

> Dica: utilize `openssl rand -hex 32` para gerar segredos aleatórios.

## 5. Construir e subir os containers

```bash
# (Opcional) obter atualizações do repositório
git pull

# Exportar a tag utilizada para nomear as imagens (use o hash atual)
export IMAGE_TAG=$(git rev-parse --short HEAD)

# Construir imagens e iniciar em segundo plano
docker compose pull  # caso existam imagens publicadas
docker compose up -d --build
```

O compose iniciará os seguintes componentes: Postgres, MongoDB, Redis, serviços FastAPI (auth, documents, agent, billing), o worker de OCR e o NGINX que faz o roteamento externo.

Somente o NGINX publica porta na máquina host (`8080` por padrão). Os demais serviços permanecem isolados na rede interna do Docker, servindo apenas como upstreams para o proxy reverso.

As variáveis `IMAGE_REGISTRY` e `IMAGE_TAG` controlam os nomes das imagens geradas. Localmente você pode mantê-las como `agente-mei` e `dev`, mas em produção defina `IMAGE_REGISTRY` para o registry usado (ex.: `ghcr.io/<org>/<repo>`) e reutilize o `IMAGE_TAG` gerado a partir do commit publicado.

Para acompanhar os logs:

```bash
docker compose logs -f
```

Os serviços FastAPI, o worker, o frontend e o NGINX enviam logs para `stdout/stderr`. Assim, ferramentas de coleta como Elastic Agent ou Stackdriver conseguem centralizar erros e métricas direto dos logs de container. O NGINX já escreve no formato JSON para simplificar o parse nessas plataformas.

## 6. Persistência e backups

Os volumes nomeados definidos no `docker-compose.yml` armazenam os dados do Postgres e do MongoDB. Faça snapshots periódicos da VM ou utilize os scripts de backup descritos abaixo.

## 7. Backups

### Execução manual

```bash
./scripts/backup_postgres.sh
./scripts/backup_mongo.sh
```

Os artefatos são gravados em `./backups/postgres` e `./backups/mongo` dentro do diretório do projeto na VM.

### Agendamento (exemplo)

Para agendar um backup diário às 2h, adicione a seguinte entrada ao crontab do usuário que executa o Docker (ajuste o caminho conforme necessário):

```cron
0 2 * * * cd /caminho/para/backend_agente_mei && ./scripts/backup_postgres.sh && ./scripts/backup_mongo.sh >> /var/log/mei_backups.log 2>&1
```

Certifique-se de que o usuário do cron possua permissão para executar `docker exec` sem senha.

## 8. Testar os endpoints externos

Após o `docker compose up`, valide se o NGINX está respondendo na porta `8080` (ajuste `<IP-OU-DOMINIO>`):

```bash
curl http://<IP-OU-DOMINIO>:8080/api/auth/health
curl http://<IP-OU-DOMINIO>:8080/api/documents/health
curl http://<IP-OU-DOMINIO>:8080/api/agent/health
curl http://<IP-OU-DOMINIO>:8080/api/billing/health
curl http://<IP-OU-DOMINIO>:8080/healthz
```

Cada endpoint deve retornar `200 OK` com uma resposta JSON de saúde do respectivo serviço.
Esse é o check rápido pós-deploy para confirmar que o roteamento do gateway está preservando o prefixo das rotas de saúde.
O endpoint `/healthz` é servido diretamente pelo NGINX e pode ser utilizado como health check do load balancer ou do orquestrador.

## 9. Habilitar HTTPS com load balancer

Para evitar gerenciar certificados dentro da VM, utilize o load balancer do provedor de nuvem para terminar TLS e encaminhar tráfego HTTP para a porta `8080` do NGINX:

1. Crie um listener HTTPS no load balancer, anexe o certificado (Let’s Encrypt ou gerenciado pelo provedor) e aponte o backend para a porta `8080` da VM.
2. Configure o health check do LB para usar HTTP (porta `8080`) em um dos endpoints de saúde, como `/api/auth/health`.
3. Mantenha o `docker-compose.yml` padrão, que publica apenas a porta `8080` e não carrega `ssl.conf`. O NGINX não precisa conhecer certificados.

> Dica: se, futuramente, for necessário terminar TLS diretamente na VM, adicione novamente um bloco `listen 443 ssl` em `nginx/ssl.conf` e exponha a porta `443` no `docker-compose.yml` com os certificados montados em `/etc/letsencrypt`.

## 10. Atualizações futuras

Para publicar uma nova versão:

```bash
git pull
export IMAGE_TAG=$(git rev-parse --short HEAD)
docker compose up -d --build
```

Para desligar o ambiente:

```bash
docker compose down
```

Com isso, o MVP ficará disponível externamente, com upload de documentos, OCR, dashboard e chat passando pelo gateway NGINX.

## 11. Pipeline CI/CD

Os merges na branch `main` disparam o workflow `.github/workflows/ci-cd.yml`. O job executa os testes automatizados via `pytest` (instalando previamente todas as dependências descritas em `requirements-test.txt`) e, somente em caso de sucesso, constrói as imagens Docker de todos os serviços (`auth`, `documents`, `agent`, `billing`, `worker`, `frontend` e `nginx`).

Cada build é publicado no GitHub Container Registry (`ghcr.io/<owner>/<repo>/<servico>:<git-sha>`), permitindo que o ambiente remoto faça `docker compose pull` e utilize as mesmas versões já validadas na pipeline. Assim, os health checks configurados no NGINX e o monitoramento centralizado via logs ficam alinhados com a versão efetivamente publicada.
