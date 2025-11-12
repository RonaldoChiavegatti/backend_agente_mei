-- Habilita a extensão para UUIDs se não estiver habilitada
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS plpgsql;

-- Tabela de Usuários (Auth Service)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Agentes (Agent Orchestrator)
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Capacidades do Agente (Agent Orchestrator)
-- Ex: '''chat''', '''document_processing'''
CREATE TABLE IF NOT EXISTS agent_capabilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    capability_type VARCHAR(100) NOT NULL,
    config_json JSONB, -- Configurações específicas, como system prompts para chat
    UNIQUE(agent_id, capability_type)
);

-- Tabela da Base de Conhecimento (Agent Orchestrator)
-- A coluna '''embedding''' requer a extensão pgvector ou similar.
CREATE TABLE IF NOT EXISTS knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(100) DEFAULT '''documentation''', -- '''documentation''', '''faq''', etc.
    embedding JSONB, -- Alterado para JSONB para compatibilidade inicial. Pode ser trocado por VECTOR.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Documentos / Jobs de Processamento (Document Service)
CREATE TYPE processing_status AS ENUM ('''pendente''', '''processando''', '''concluido''', '''falhou''');
CREATE TYPE document_type AS ENUM (
    '''NOTA_FISCAL_EMITIDA''',
    '''NOTA_FISCAL_RECEBIDA''',
    '''INFORME_BANCARIO''',
    '''DESPESA_DEDUTIVEL''',
    '''INFORME_RENDIMENTOS''',
    '''DASN_SIMEI''',
    '''RECIBO_IR_ANTERIOR''',
    '''DOC_IDENTIFICACAO''',
    '''COMPROVANTE_ENDERECO'''
);

CREATE TABLE IF NOT EXISTS document_processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_path VARCHAR(1024) NOT NULL, -- Caminho no MinIO
    document_type document_type NOT NULL,
    status processing_status NOT NULL DEFAULT '''processando''',
    extracted_data JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Saldos de Usuário (Billing Service)
CREATE TABLE IF NOT EXISTS user_balances (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    balance BIGINT NOT NULL DEFAULT 0, -- Saldo em tokens/créditos
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Transações (Billing Service)
CREATE TYPE transaction_type AS ENUM ('''CHARGE''', '''REFUND''', '''INITIAL''');

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount BIGINT NOT NULL,
    type transaction_type NOT NULL,
    description TEXT,
    related_job_id UUID, -- Opcional, para vincular a um job específico
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para otimizar consultas comuns
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_doc_jobs_user_id ON document_processing_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_agent_id ON knowledge_base(agent_id);

-- Triggers para atualizar o campo '''updated_at''' automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language plpgsql;

CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_doc_jobs_updated_at
BEFORE UPDATE ON document_processing_jobs
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_balances_last_updated
BEFORE UPDATE ON user_balances
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
