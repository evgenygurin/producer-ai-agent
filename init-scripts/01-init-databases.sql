-- Create databases
CREATE DATABASE IF NOT EXISTS n8n;

-- Enable pgvector extension for R2R
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS r2r;
CREATE SCHEMA IF NOT EXISTS metadata;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE r2r TO postgres;
GRANT ALL PRIVILEGES ON DATABASE n8n TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA r2r TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA metadata TO postgres;

-- Create metadata tables for user data
CREATE TABLE IF NOT EXISTS metadata.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth0_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metadata.workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES metadata.users(id),
    n8n_workflow_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metadata.rag_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES metadata.users(id),
    workflow_id UUID REFERENCES metadata.workflows(id),
    r2r_collection_id UUID,
    session_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_users_auth0_id ON metadata.users(auth0_id);
CREATE INDEX idx_users_email ON metadata.users(email);
CREATE INDEX idx_workflows_user_id ON metadata.workflows(user_id);
CREATE INDEX idx_workflows_n8n_id ON metadata.workflows(n8n_workflow_id);
CREATE INDEX idx_rag_sessions_user_id ON metadata.rag_sessions(user_id);
CREATE INDEX idx_rag_sessions_workflow_id ON metadata.rag_sessions(workflow_id);
