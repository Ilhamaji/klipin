-- Klipin database schema (PostgreSQL / Supabase)
-- Run this once on a fresh database before starting the backend.
-- The AI service also creates queries.model_comparison automatically, but
-- defining it here keeps a fresh install consistent.

BEGIN;

CREATE TABLE IF NOT EXISTS users (
  user_id    SERIAL PRIMARY KEY,
  username   VARCHAR(100) NOT NULL UNIQUE,
  password   TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notes (
  id         SERIAL PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  title      TEXT,
  contents   TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS queries (
  id               SERIAL PRIMARY KEY,
  user_id          INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  query_text       TEXT NOT NULL,
  embedding        JSON NOT NULL,
  model_comparison JSON,
  created_at       TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS articles (
  id              SERIAL PRIMARY KEY,
  query_id        INTEGER NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
  title           TEXT NOT NULL,
  url             TEXT NOT NULL,
  abstract        TEXT,
  authors         JSON,
  year            VARCHAR(4) NOT NULL,
  subject         VARCHAR(100),
  jenjang         VARCHAR(100),
  relevance_score REAL,
  confidence      REAL,
  created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS saved_articles (
  id         SERIAL PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT saved_articles_user_article_unique UNIQUE (user_id, article_id)
);

CREATE INDEX IF NOT EXISTS notes_user_id_idx ON notes(user_id);
CREATE INDEX IF NOT EXISTS queries_user_id_idx ON queries(user_id);
CREATE INDEX IF NOT EXISTS articles_query_id_idx ON articles(query_id);
CREATE INDEX IF NOT EXISTS saved_articles_user_id_idx ON saved_articles(user_id);
CREATE INDEX IF NOT EXISTS saved_articles_article_id_idx ON saved_articles(article_id);

COMMIT;