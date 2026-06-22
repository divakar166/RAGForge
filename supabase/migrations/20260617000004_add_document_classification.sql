-- Migration: add_document_classification
-- Adds classification-based RBAC to the documents table.

ALTER TABLE public.documents
ADD COLUMN IF NOT EXISTS classification VARCHAR(32) NOT NULL DEFAULT 'internal';

-- Existing rows get 'internal' classification by default.
-- The allowed_roles column is kept for backward compat but will be
-- derived from classification at document processing time.
