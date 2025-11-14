# Serviço de Faturamento (`billing_service`)

Este serviço é responsável por gerenciar o saldo e as transações financeiras dos usuários.

## Responsabilidades

- **Controle de Saldo:** Mantém o registro do saldo de tokens de cada usuário.
- **Cobrança:** Fornece um endpoint interno para que outros serviços (como o `agent_orchestrator`) possam debitar tokens do saldo do usuário.
- **Histórico de Transações:** Armazena um registro de todas as transações (débitos e créditos) na conta de um usuário.

## API Endpoints

A base da URL para este serviço é `/billing`.

### `POST /charge-tokens`

Endpoint **interno** para debitar um valor do saldo do usuário. Este endpoint é projetado para ser chamado por outros serviços, não diretamente por um cliente frontend.

- **Request Body:**
  ```json
  {
    "user_id": "uuid",
    "amount": "integer",
    "description": "string"
  }
  ```

- **Response (200 OK):**
  ```json
  {
    "status": "success"
  }
  ```

- **Possíveis Erros:**
  - `402 PAYMENT_REQUIRED`: Saldo insuficiente ou usuário não encontrado.

### `GET /balance/{user_id}`

Retorna o saldo atual de um usuário.

- **Parâmetros de URL:**
  - `user_id`: O ID do usuário.

- **Response (200 OK):**
  ```json
  {
    "user_id": "uuid",
    "balance": "integer"
  }
  ```

- **Possíveis Erros:**
  - `404 NOT_FOUND`: Usuário não encontrado.

### `GET /transactions/{user_id}`

Retorna uma lista de todas as transações de um usuário.

- **Parâmetros de URL:**
  - `user_id`: O ID do usuário.

- **Response (200 OK):**
  ```json
  [
    {
      "id": "uuid",
      "user_id": "uuid",
      "amount": "integer",
      "description": "string",
      "created_at": "datetime"
    }
  ]
  ```

- **Possíveis Erros:**
  - `404 NOT_FOUND`: Usuário não encontrado.

### `GET /monthly-usage/{user_id}`

Retorna um resumo agregado de uso de tokens do usuário no mês corrente.

- **Parâmetros de URL:**
  - `user_id`: O ID do usuário.

- **Response (200 OK):**
  ```json
  {
    "user_id": "uuid",
    "tokens_consumed": "integer",
    "consultations_count": "integer",
    "start_date": "datetime",
    "end_date": "datetime"
  }
  ```

- **Observações:**
  - Retorna `0` para os campos de contagem e consumo quando não houver consultas no período.

## Dependências

As principais dependências deste serviço são:

- `fastapi`: Para a criação da API.
- `pydantic`: Para validação de dados.
- `psycopg2-binary`: Driver do PostgreSQL.

## Variáveis de Ambiente

Estas são as variáveis de ambiente necessárias para configurar o serviço:

- `DATABASE_URL`: URL de conexão com o banco de dados PostgreSQL. Ex: `postgresql://user:password@host:port/database`
