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
   - **NGINX_HOST_PORT:** defina `80` para expor o gateway diretamente na porta HTTP padrão. Para usar HTTPS através de um load balancer externo, mantenha o valor conforme a necessidade.

> Dica: utilize `openssl rand -hex 32` para gerar segredos aleatórios.

## 5. Construir e subir os containers

```bash
# (Opcional) obter atualizações do repositório
git pull

# Construir imagens e iniciar em segundo plano
docker compose pull  # caso existam imagens publicadas
docker compose up -d --build
```

O compose iniciará os seguintes componentes: Postgres, MongoDB, Redis, serviços FastAPI (auth, documents, agent, billing), o worker de OCR e o NGINX que faz o roteamento externo.

Para acompanhar os logs:

```bash
docker compose logs -f
```

## 6. Persistência e backups

Os volumes nomeados definidos no `docker-compose.yml` armazenam os dados do Postgres e do MongoDB. Faça snapshots periódicos da VM ou utilize `docker cp`/`pg_dump`/`mongodump` para backups em produção.

## 7. Testar os endpoints externos

Após o `docker compose up`, valide se o NGINX está respondendo (ajuste `<IP-OU-DOMINIO>`):

```bash
curl http://<IP-OU-DOMINIO>/api/auth/health
curl http://<IP-OU-DOMINIO>/api/documents/health
```

Cada endpoint deve retornar `200 OK` com uma resposta JSON de saúde do respectivo serviço.

## 8. Habilitar HTTPS (opcional)

Se quiser expor HTTPS diretamente na VM:

1. Instale o Certbot (`sudo snap install --classic certbot`).
2. Crie um arquivo `nginx/ssl.conf` com o bloco de servidor HTTPS desejado ou adapte `nginx.conf`.
3. Atualize o `docker-compose.yml` para montar a configuração HTTPS e recarregue o compose.

Alternativamente, utilize um load balancer/reverse proxy do provedor de nuvem que termine TLS e encaminhe para a porta `80` da VM.

## 9. Atualizações futuras

Para publicar uma nova versão:

```bash
git pull
docker compose up -d --build
```

Para desligar o ambiente:

```bash
docker compose down
```

Com isso, o MVP ficará disponível externamente, com upload de documentos, OCR, dashboard e chat passando pelo gateway NGINX.
