create extension if not exists vector;

create table if not exists document_chunks (
  id text primary key,
  source_id text,
  url text,
  title text,
  source_type text,
  scheme_name text,
  topic text,
  chunk_text text,
  embedding vector(384),
  created_at timestamptz default now()
);

create index if not exists document_chunks_embedding_idx
on document_chunks
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

create or replace function match_document_chunks(
  query_embedding vector(384),
  match_count int
)
returns table (
  id text,
  source_id text,
  url text,
  title text,
  source_type text,
  scheme_name text,
  topic text,
  chunk_text text,
  similarity float
)
language sql
stable
as $$
  select
    document_chunks.id,
    document_chunks.source_id,
    document_chunks.url,
    document_chunks.title,
    document_chunks.source_type,
    document_chunks.scheme_name,
    document_chunks.topic,
    document_chunks.chunk_text,
    1 - (document_chunks.embedding <=> query_embedding) as similarity
  from document_chunks
  where document_chunks.embedding is not null
  order by document_chunks.embedding <=> query_embedding
  limit match_count;
$$;
