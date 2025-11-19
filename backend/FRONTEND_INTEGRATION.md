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

## Catálogo de Rotas e Contratos

Os trechos a seguir detalham todos os endpoints expostos pelos serviços FastAPI (descobertos com `rg "@router" backend/services/*/infrastructure/web`). Para cada rota listamos formato esperado, payloads de exemplo e códigos de erro relevantes. Todos os exemplos assumem a URL base `http://localhost:8080/api`.

### Serviço de Autenticação (`/auth`)

#### `POST /auth/register`
- **Descrição:** cria um usuário.
- **Body (`application/json`):**
  ```json
  {
    "full_name": "Seu Nome",
    "email": "seu@email.com",
    "password": "senhaSegura123"
  }
  ```
- **Resposta 201 (`application/json`):**
  ```json
  {
    "id": "6d4ddcfe-7b9d-4e8c-861b-402bfb72f5cd",
    "full_name": "Seu Nome",
    "email": "seu@email.com",
    "created_at": "2024-03-18T12:34:56.000000",
    "updated_at": "2024-03-18T12:34:56.000000"
  }
  ```
- **Códigos de erro:** `422` (senha vazia), `409` (e-mail já usado), `500` (erro inesperado).

#### `POST /auth/login`
- **Descrição:** autentica usando formulário OAuth2 padrão.
- **Body (`application/x-www-form-urlencoded`):**
  - `username`: e-mail usado no cadastro
  - `password`: senha
- **Resposta 200:**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```
- **Códigos de erro:** `401` (credenciais inválidas, inclui cabeçalho `WWW-Authenticate: Bearer`), `500`.

#### `GET /auth/me`
- **Descrição:** retorna o perfil completo do usuário autenticado.
- **Resposta 200:** estrutura igual ao retorno de cadastro (campos `id`, `full_name`, `email`, `created_at`, `updated_at`).
- **Códigos de erro:** `404` (usuário não encontrado), `500`.

#### `GET /auth/profile`
- **Descrição:** retorna a versão resumida do perfil (ideal para cabeçalhos do app).
- **Resposta 200:**
  ```json
  {
    "email": "seu@email.com",
    "created_at": "2024-03-18T12:34:56.000000"
  }
  ```
- **Códigos de erro:** `404`, `500`.

### Serviço de Agentes (`/chat`)

#### `POST /chat`
- **Descrição:** envia uma mensagem para um agente orquestrado.
- **Body (`application/json`):**
  ```json
  {
    "agent_id": "0dbbd8ab-97a1-4b46-b6f3-4ec734b5c3af",
    "user_message": "Olá, agente!",
    "conversation_history": [
      {
        "role": "user",
        "content": "Mensagem anterior"
      }
    ]
  }
  ```
- **Resposta 200:**
  ```json
  {
    "assistant_message": "Resposta sintetizada pelo agente."
  }
  ```
- **Códigos de erro:** `404` (agente inexistente), `402` (saldo insuficiente), `500` (falha interna).

### Serviço de Documentos (`/documents`)

Os endpoints abaixo exigem `Authorization: Bearer <token>`.

#### `POST /documents/upload`
- **Descrição:** inicia o processamento de um documento.
- **Body (`multipart/form-data`):**
  - `file`: arquivo suportado
  - `document_type`: qualquer valor do enum `DocumentType` (`NOTA_FISCAL_EMITIDA`, `INFORME_BANCARIO`, etc.).
- **Resposta 202:**
  ```json
  {
    "id": "e30ed708-0179-4ef4-b588-0b2a0c21cf0f",
    "user_id": "7ebea111-9a29-4e11-a4a1-15db353b7a4f",
    "file_path": "documents/user/arquivo.pdf",
    "document_type": "NOTA_FISCAL_EMITIDA",
    "status": "processando",
    "extracted_data": null,
    "error_message": null,
    "created_at": "2024-03-18T12:34:56.000000",
    "updated_at": "2024-03-18T12:34:56.000000"
  }
  ```
- **Códigos de erro:** `400` (dados inválidos), `500`.

#### `GET /documents/jobs/{job_id}`
- **Descrição:** recupera status do job; resposta igual ao exemplo acima.
- **Códigos de erro:** `404` (job inexistente), `403` (usuário não é dono), `500`.

#### `GET /documents/jobs/{job_id}/details`
- **Descrição:** retorna payload enriquecido com extrações, histórico e metadados.
- **Resposta 200 (campos principais):**
  ```json
  {
    "id": "e30ed708-0179-4ef4-b588-0b2a0c21cf0f",
    "document_type": "NOTA_FISCAL_EMITIDA",
    "document_label": "Nota Fiscal 123",
    "status": "concluido",
    "source_group": "nota_fiscal",
    "source_group_label": "Notas fiscais emitidas",
    "origem_legivel": "Valores extraídos de notas fiscais emitidas",
    "valor": 1500.0,
    "valor_formatado": "R$ 1.500,00",
    "data": "2024-03-10",
    "data_formatada": "10/03/2024",
    "natureza": "receita",
    "categoria": "faturamento mei",
    "resumo": "Nota fiscal emitida em 10/03",
    "extras": {
      "tomador": {
        "nome": "Empresa XYZ"
      }
    },
    "raw_extracted_data": {"numero": "123"},
    "history": [
      {
        "version": 1,
        "author_type": "system",
        "created_at": "2024-03-18T12:34:56.000000",
        "data_snapshot": {"valor": 1500},
        "changes": [
          {"field_path": "valor", "previous_value": null, "current_value": 1500}
        ]
      }
    ],
    "created_at": "2024-03-18T12:34:56.000000",
    "updated_at": "2024-03-18T12:34:56.000000"
  }
  ```
- **Códigos de erro:** `404`, `403`, `500`.

#### `GET /documents/jobs`
- **Descrição:** lista jobs do usuário autenticado; aceita `document_type` como query para filtrar.
- **Resposta 200:** array de objetos `DocumentJob` conforme exemplo do upload.
- **Códigos de erro:** `500`.

#### `GET /documents/dashboard/annual-revenue`
- **Query params opcionais:** `year` (`2000-2100`).
- **Resposta 200:**
  ```json
  {
    "ano": 2024,
    "faturamento_total": 48000.0,
    "faturamento_total_formatado": "R$ 48.000,00",
    "limite_anual": 81000.0,
    "limite_anual_formatado": "R$ 81.000,00",
    "destaque": "Você já atingiu 59% do limite anual.",
    "detalhamento": {
      "NOTA_FISCAL_EMITIDA": {
        "document_type": "NOTA_FISCAL_EMITIDA",
        "label": "Notas fiscais",
        "total": 42000.0,
        "total_formatado": "R$ 42.000,00",
        "documentos": ["a8c3..."],
        "quantidade_documentos": 12
      }
    },
    "observacoes": ["Considere revisar suas despesas."],
    "documentos_considerados": ["Notas fiscais emitidas"],
    "alerta_limite": {
      "nivel": "atencao",
      "mensagem": "Faturamento acima de 60% do limite.",
      "percentual_utilizado": 0.59,
      "percentual_utilizado_formatado": "59%"
    }
  }
  ```
- **Códigos de erro:** `500`.

#### `GET /documents/dashboard/monthly-revenue`
- **Query params opcionais:** `year` (2000–2100) e `month` (1–12).
- **Resposta 200:**
  ```json
  {
    "mes": 3,
    "ano": 2024,
    "faturamento_total": 12000.0,
    "faturamento_total_formatado": "R$ 12.000,00",
    "limite_mensal": 6750.0,
    "limite_mensal_formatado": "R$ 6.750,00",
    "destaque": "Você está acima do limite mensal.",
    "detalhamento": {},
    "observacoes": [],
    "documentos_considerados": []
  }
  ```
- **Códigos de erro:** `400` (valores fora do intervalo), `500`.

#### `GET /documents/dashboard/basic-metrics`
- **Resposta 200:**
  ```json
  {
    "reference_year": 2024,
    "reference_month": 3,
    "counters": [
      {
        "key": "documents_processed",
        "title": "Documentos processados",
        "subtitle": "Últimos 30 dias",
        "value": 42
      }
    ]
  }
  ```
- **Códigos de erro:** `500`.

#### `PATCH /documents/jobs/{job_id}/extracted-data`
- **Descrição:** sobrescreve o payload extraído manualmente.
- **Body (`application/json`):**
  ```json
  {
    "data": {
      "valor": 1800.0,
      "cliente": "Empresa XYZ"
    }
  }
  ```
- **Resposta 200:** retorna `DocumentDetailsResponse` atualizado (mesma estrutura do endpoint de detalhes).
- **Códigos de erro:** `404`, `403`, `500`.

### Serviço de Faturamento (`/billing`)

#### `POST /billing/charge-tokens`
- **Descrição:** uso interno para debitar tokens.
- **Body (`application/json`):**
  ```json
  {
    "user_id": "7ebea111-9a29-4e11-a4a1-15db353b7a4f",
    "amount": 50,
    "description": "Consulta com agente especialista"
  }
  ```
- **Resposta 200:** `{ "status": "success" }`
- **Códigos de erro:** `402` (saldo insuficiente ou usuário inexistente).

#### `GET /billing/balance/{user_id}`
- **Descrição:** retorna saldo do usuário autenticado (precisa coincidir com o `user_id` do token).
- **Resposta 200:**
  ```json
  {
    "user_id": "7ebea111-9a29-4e11-a4a1-15db353b7a4f",
    "balance": 1200,
    "last_updated_at": "2024-03-18T12:34:56.000000"
  }
  ```
- **Códigos de erro:** `403` (ID divergente), `404` (usuário desconhecido).

#### `GET /billing/transactions/{user_id}`
- **Descrição:** histórico de consumo.
- **Resposta 200:**
  ```json
  [
    {
      "id": "ad8b7551-425f-4f69-9590-3d1c99d23141",
      "date": "2024-03-18T10:15:00.000000",
      "tokens": 25,
      "consultation_type": "chat",
      "description": "Conversa com agente fiscal",
      "document_type": "NOTA_FISCAL_EMITIDA"
    }
  ]
  ```
- **Códigos de erro:** `403`, `404`.

#### `GET /billing/monthly-usage/{user_id}`
- **Descrição:** resumo agregado de uso dentro do mês corrente.
- **Resposta 200:**
  ```json
  {
    "user_id": "7ebea111-9a29-4e11-a4a1-15db353b7a4f",
    "tokens_consumed": 250,
    "consultations_count": 12,
    "start_date": "2024-03-01T00:00:00.000000",
    "end_date": "2024-03-31T23:59:59.000000"
  }
  ```
- **Códigos de erro:** `403` (ID divergente). O serviço retorna 200 mesmo quando não há dados; ajuste o frontend conforme necessário.

> ⚠️ Lembre-se: rotas contendo `{user_id}` exigem que o valor informado seja exatamente o ID presente no token JWT, caso contrário o backend responde `403 Forbidden` antes mesmo de consultar o serviço.
