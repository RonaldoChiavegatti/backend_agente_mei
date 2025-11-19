# Visão Geral do Projeto

Este projeto é um sistema de backend modular construído com uma arquitetura de microserviços. Cada serviço é responsável por uma área de negócio específica, promovendo a separação de responsabilidades, escalabilidade e manutenibilidade.

## Arquitetura

A arquitetura segue o padrão de microserviços, com cada serviço sendo um componente independente e fracamente acoplado. A comunicação entre os serviços e o mundo exterior é feita através de um API Gateway, que atua como um ponto de entrada único para todas as requisições.

Os principais componentes da arquitetura são:

- **API Gateway (Nginx):** Roteia as requisições para os serviços apropriados.
- **Serviços de Backend (Python/FastAPI):** Implementam a lógica de negócio.
- **Banco de Dados (PostgreSQL):** Persiste os dados de cada serviço.
- **Cache (Redis):** Usado para cache e como message broker.
- **Armazenamento de Arquivos (Minio):** Armazena arquivos e documentos.

Para mais detalhes, consulte o arquivo [ARCHITECTURE.md](ARCHITECTURE.md).

## Serviços

O sistema é composto pelos seguintes serviços:

- **Serviço de Autenticação (`auth_service`):** Responsável pelo registro, login e gerenciamento de usuários.
- **Serviço de Orquestração de Agentes (`agent_orchestrator`):** Gerencia os agentes de IA, suas conversas e conhecimento.
- **Serviço de Faturamento (`billing_service`):** Controla o saldo e as transações dos usuários.
- **Serviço de Documentos (`document_service`):** Lida com o upload, processamento e armazenamento de documentos.

Cada serviço possui seu próprio `README.md` com informações detalhadas.

## Como Executar o Projeto

Para executar o projeto, você precisa ter o Docker e o Docker Compose instalados.

1. **Clone o repositório:**
   ```bash
   git clone <url-do-repositorio>
   cd backend
   ```

2. **Suba os containers:**
   ```bash
   docker-compose -f docker/docker-compose.yml up --build
   ```

Os serviços estarão disponíveis nos seguintes endereços:

- **API Gateway (via Nginx):** `http://localhost:8080/api`
- **Serviço de Autenticação:** acessível internamente no cluster Docker como `http://auth:8000`
- **Serviço de Orquestração de Agentes:** acessível como `http://agent:8000`
- **Serviço de Documentos:** acessível como `http://documents:8000`
- **Serviço de Faturamento:** acessível como `http://billing:8000`

## Conectando um Frontend

Para instruções sobre como conectar uma aplicação frontend a este backend, consulte o arquivo [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md).
