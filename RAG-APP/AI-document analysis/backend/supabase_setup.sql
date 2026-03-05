-- =============================================================
-- Supabase pgvector Setup for RAG Document Analysis
-- Run this in your Supabase Dashboard → SQL Editor
-- =============================================================

-- 1. Enable the vector extension
create extension if not exists vector;

-- 2. Create the embeddings table
-- BGE-small-en-v1.5 produces 384-dimensional embeddings
create table if not exists document_embeddings (
  id bigserial primary key,
  project_id text not null,
  paper_id text not null,
  content text not null,
  metadata jsonb default '{}',
  embedding vector(384) not null,
  created_at timestamptz default now()
);

-- 3. Create indexes for fast lookups
create index if not exists idx_doc_embeddings_project
  on document_embeddings (project_id);

create index if not exists idx_doc_embeddings_paper
  on document_embeddings (project_id, paper_id);

-- 4. Create the similarity search function
-- Uses L2 distance (lower = more similar) to match existing behavior
create or replace function match_documents(
  query_embedding vector(384),
  match_project_id text,
  match_count int default 5
)
returns table (
  id bigint,
  project_id text,
  paper_id text,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    de.id,
    de.project_id,
    de.paper_id,
    de.content,
    de.metadata,
    (de.embedding <-> query_embedding)::float as similarity
  from document_embeddings de
  where de.project_id = match_project_id
  order by de.embedding <-> query_embedding
  limit match_count;
end;
$$;
