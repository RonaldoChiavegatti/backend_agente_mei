# Guia de Integração com o Frontend

Este documento fornece instruções sobre como conectar uma aplicação frontend ao backend deste projeto.

## Ponto de Entrada: O API Gateway

Todas as requisições da sua aplicação frontend devem ser direcionadas para o API Gateway, que é o ponto de entrada único para o backend. O Gateway é responsável por rotear sua requisição para o microserviço correto.

**URL Base do API Gateway:** `http://localhost:8080/api`

## Fluxo de Autenticação

A maioria das rotas do backend é protegida e requer um token de autenticação. O fluxo para obter e usar um token é o seguinte:

### 1. Registrar um Novo Usuário

Primeiro, crie uma conta de usuário.

- **Endpoint:** `POST /auth/register`
- **URL Completa:** `http://localhost:8080/api/auth/register`
- **Body:**
  ```json
  {
    "full_name": "Seu Nome",
    "email": "seu@email.com",
    "password": "sua_senha"
  }
  ```

### 2. Fazer Login para Obter um Token

Após o registro, faça login para receber um token de acesso JWT (JSON Web Token).

- **Endpoint:** `POST /auth/login`
- **URL Completa:** `http://localhost:8080/api/auth/login`
- **Body (form-data):**
  - `username`: `seu@email.com`
  - `password`: `sua_senha`

- **Resposta:**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```

### 3. Enviar o Token nas Requisições

Para todas as requisições a endpoints protegidos, você deve incluir o `access_token` no cabeçalho `Authorization`.

- **Cabeçalho:** `Authorization: Bearer <seu_access_token>`

## Endpoints Disponíveis via API Gateway

Abaixo estão os principais endpoints que você pode consumir a partir do seu frontend.

### Serviço de Autenticação (`/auth`)

- `POST /auth/register`: Registra um novo usuário.
- `POST /auth/login`: Autentica um usuário e retorna um token.
- `GET /auth/profile`: Retorna o e-mail e a data de cadastro do usuário autenticado. **(Requer autenticação)**

### Serviço de Agentes (`/chat`)

- `POST /chat`: Envia uma mensagem para um agente de IA. **(Requer autenticação)**
  - **URL:** `http://localhost:8080/api/chat`
  - **Exemplo de Body:**
    ```json
    {
      "agent_id": "...",
      "user_message": "Olá, agente!",
      "conversation_history": []
    }
    ```

### Serviço de Documentos (`/documents`)

- `POST /documents/upload`: Faz o upload de um arquivo para processamento. **(Requer autenticação)**
  - **URL:** `http://localhost:8080/api/documents/upload`
  - **Body:** `multipart/form-data` com um campo `file`.

- `GET /documents/jobs/{job_id}`: Consulta o status de um trabalho de processamento. **(Requer autenticação)**
  - **URL:** `http://localhost:8080/api/documents/jobs/<job_id>`

- `GET /documents/jobs`: Lista todos os trabalhos de um usuário. **(Requer autenticação)**
  - **URL:** `http://localhost:8080/api/documents/jobs`

### Serviço de Faturamento (`/billing`)

Os endpoints de faturamento são, em sua maioria, para comunicação interna entre serviços, mas você pode querer expor o saldo e o histórico para o usuário.

- `GET /billing/balance/{user_id}`: Retorna o saldo do usuário. **(Requer autenticação e que o `user_id` seja o do usuário autenticado)**
  - **URL:** `http://localhost:8080/api/billing/balance/<user_id>`

- `GET /billing/transactions/{user_id}`: Retorna o histórico de transações do usuário. **(Requer autenticação e que o `user_id` seja o do usuário autenticado)**
  - **URL:** `http://localhost:8080/api/billing/transactions/<user_id>`

Lembre-se de que, para os endpoints que incluem `{user_id}` no path, você precisará obter o ID do usuário autenticado, que geralmente está contido no payload do token JWT.
