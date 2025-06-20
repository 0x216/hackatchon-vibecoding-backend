-- Initialize database with extensions and basic setup

-- Create pgvector extension if available
CREATE EXTENSION IF NOT EXISTS vector;

-- Create user and database (if not exists)
-- These are already created by the PostgreSQL Docker image

-- Set some useful defaults
ALTER DATABASE legalrag SET timezone TO 'UTC';

-- Create indexes that will be useful for our application
-- Note: Table creation will be handled by SQLAlchemy/Alembic

-- Log successful initialization
-- INSERT INTO pg_stat_statements_info (dealloc) VALUES (0) ON CONFLICT DO NOTHING; 