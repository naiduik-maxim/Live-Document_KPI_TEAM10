-- psql script. Run from this directory against the isolated server.
-- The name is intentionally distinct from the application database.
\set ON_ERROR_STOP on
CREATE DATABASE living_documents_sql_protocol;
\connect living_documents_sql_protocol
\ir 01_schema.sql
SET search_path TO public;
\ir 02_seed.sql
