# Serviço de Documentos (`document_service`)

Este serviço gerencia o upload, processamento e consulta de documentos.

## Responsabilidades

- **Upload de Arquivos:** Recebe arquivos dos usuários e os armazena de forma segura no Minio.
- **Processamento Assíncrono:** Inicia tarefas de processamento de documentos (como OCR) de forma assíncrona usando uma fila no Redis.
- **Consulta de Status:** Permite que os usuários consultem o status de seus trabalhos de processamento.
- **Listagem de Trabalhos:** Permite que os usuários listem todos os seus trabalhos de processamento.

## Arquitetura de Processamento

1. O cliente envia um arquivo para o endpoint `/upload`.
2. O serviço `document_service` salva o arquivo no Minio e cria um `DocumentJob` no banco de dados com o status inicial `processando` e o `document_type` informado.
3. Uma mensagem contendo o `job_id` é enviada para a fila `ocr_jobs` no Redis.
4. O `document-worker` (um processo separado) consome a mensagem da fila.
5. O worker usa o `job_id` para buscar os detalhes do trabalho, baixa o arquivo do Minio, executa o processamento (ex: OCR) e atualiza o status do `DocumentJob` para `COMPLETED` ou `FAILED`.

## API Endpoints

A base da URL para este serviço é `/documents`.

### `POST /upload`

Faz o upload de um documento para processamento.

- **Header de Autenticação:**
  - `Authorization: Bearer <seu-token-jwt>`

- **Request Body (form-data):**
- `file`: O arquivo a ser enviado (formatos suportados: PDF, JPG, PNG).
- `document_type`: Tipo do documento de acordo com os valores aceitos (ex.: `NOTA_FISCAL_EMITIDA`).

- **Response (202 ACCEPTED):**
  Retorna o trabalho de processamento que foi criado.
  ```json
  {
    "id": "uuid",
    "user_id": "uuid",
    "file_path": "string",
    "document_type": "NOTA_FISCAL_EMITIDA",
    "status": "processando",
    "created_at": "datetime"
  }
  ```

### `GET /jobs/{job_id}`

Consulta o status de um trabalho de processamento específico.

- **Header de Autenticação:**
  - `Authorization: Bearer <seu-token-jwt>`

- **Parâmetros de URL:**
  - `job_id`: O ID do trabalho.

- **Response (200 OK):**
  ```json
  {
    "id": "uuid",
    "user_id": "uuid",
    "file_path": "string",
    "document_type": "NOTA_FISCAL_EMITIDA",
    "status": "processando" | "concluido" | "falhou",
    "created_at": "datetime"
  }
  ```

- **Possíveis Erros:**
  - `403 FORBIDDEN`: O usuário não tem permissão para ver este trabalho.
  - `404 NOT_FOUND`: Trabalho não encontrado.

### `GET /jobs`

Lista todos os trabalhos de processamento de um usuário.

- **Header de Autenticação:**
  - `Authorization: Bearer <seu-token-jwt>`

- **Response (200 OK):**
  ```json
  [
    {
      "id": "uuid",
      "user_id": "uuid",
      "file_path": "string",
      "document_type": "NOTA_FISCAL_EMITIDA",
      "status": "processando" | "concluido" | "falhou",
      "created_at": "datetime"
    }
  ]
  ```

## Dependências

- `fastapi`: Para a criação da API.
- `pydantic`: Para validação de dados.
- `psycopg2-binary`: Driver do PostgreSQL.
- `minio`: Cliente para o Minio.
- `redis`: Cliente para o Redis.
- `python-multipart`: Para manipulação de uploads de arquivo.

## Variáveis de Ambiente

- `DATABASE_URL`: URL de conexão com o banco de dados PostgreSQL.
- `MINIO_ENDPOINT`: Endpoint do serviço Minio. Ex: `minio:9000`
- `MINIO_ACCESS_KEY`: Chave de acesso do Minio.
- `MINIO_SECRET_KEY`: Chave secreta do Minio.
- `MINIO_BUCKET_NAME`: Nome do bucket no Minio (padrão: `documents`).
- `REDIS_URL`: URL de conexão com o Redis. Ex: `redis://redis:6379/0`
- `OCR_QUEUE_NAME`: Nome da fila de processamento no Redis (padrão: `ocr_jobs`).
