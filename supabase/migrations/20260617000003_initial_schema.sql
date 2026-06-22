-- RAGForge Database Schema — initial migration
-- All tables, constraints, indexes, RLS policies, and seed data.

-- 1. Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Helper: get the requesting user's ID from the custom JWT
CREATE OR REPLACE FUNCTION public.requesting_user_id()
RETURNS UUID LANGUAGE SQL STABLE
AS $$
  SELECT COALESCE(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    nullif(current_setting('request.jwt.claims', true)::json->>'sub', '')
  )::UUID;
$$;

-- 3. Tables
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(320) NOT NULL UNIQUE,
    username VARCHAR(64) NOT NULL UNIQUE,
    hashed_password VARCHAR(256) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_superuser BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_users_username ON public.users(username);

CREATE TABLE public.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(256) NOT NULL,
    slug VARCHAR(128) NOT NULL UNIQUE,
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    settings JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_organizations_slug ON public.organizations(slug);

CREATE TABLE public.organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL DEFAULT 'member',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(organization_id, user_id)
);

CREATE TABLE public.organization_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    name VARCHAR(64) NOT NULL,
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '[]',
    is_system BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(organization_id, name)
);

ALTER TABLE public.organization_members
ADD CONSTRAINT fk_organization_members_role
FOREIGN KEY (organization_id, role)
REFERENCES public.organization_roles(organization_id, name);

CREATE TABLE public.invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    email VARCHAR(320) NOT NULL,
    token VARCHAR(128) NOT NULL UNIQUE,
    role VARCHAR(32) NOT NULL DEFAULT 'member',
    invited_by_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_invitations_token ON public.invitations(token);

CREATE TABLE public.collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    name VARCHAR(256) NOT NULL,
    description TEXT,
    is_public BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    collection_id UUID REFERENCES public.collections(id) ON DELETE SET NULL,
    title VARCHAR(512) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_type VARCHAR(32) NOT NULL,
    file_size INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'uploaded',
    classification VARCHAR(32) NOT NULL DEFAULT 'internal',
    uploaded_by_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    allowed_roles TEXT[] NOT NULL DEFAULT '{member}',
    is_public_in_org BOOLEAN NOT NULL DEFAULT false,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_documents_organization_id ON public.documents(organization_id);
CREATE INDEX idx_documents_uploaded_by_id ON public.documents(uploaded_by_id);

CREATE TABLE public.conversation_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title VARCHAR(256) NOT NULL DEFAULT 'New Chat',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_threads_org_user ON public.conversation_threads(organization_id, user_id);

CREATE TABLE public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    thread_id UUID REFERENCES public.conversation_threads(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    citations JSONB,
    trace_id VARCHAR(128),
    feedback_score SMALLINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_conversations_thread_id ON public.conversations(thread_id);

CREATE TABLE public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES public.organizations(id) ON DELETE SET NULL,
    actor_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    action VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64),
    resource_id UUID,
    details JSONB,
    ip_address VARCHAR(45),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_logs_action ON public.audit_logs(action);
CREATE INDEX idx_audit_logs_timestamp ON public.audit_logs(timestamp);
CREATE INDEX idx_audit_logs_organization_id ON public.audit_logs(organization_id);

-- 4. Helper: check if the requesting user is an active member of an org
CREATE OR REPLACE FUNCTION public.is_org_member(org_id UUID)
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.organization_members
    WHERE organization_id = org_id
      AND user_id = public.requesting_user_id()
      AND is_active = true
  );
$$;

-- 5. Row Level Security

-- Users
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_self ON public.users
    FOR ALL
    USING (id = public.requesting_user_id())
    WITH CHECK (id = public.requesting_user_id());

-- Organizations
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
CREATE POLICY orgs_select ON public.organizations
    FOR SELECT
    USING (public.is_org_member(id));
CREATE POLICY orgs_update ON public.organizations
    FOR UPDATE
    USING (owner_id = public.requesting_user_id())
    WITH CHECK (owner_id = public.requesting_user_id());

-- Organization Members
ALTER TABLE public.organization_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY members_select ON public.organization_members
    FOR SELECT
    USING (user_id = public.requesting_user_id() OR public.is_org_member(organization_id));
CREATE POLICY members_insert ON public.organization_members
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.organization_members om
            WHERE om.organization_id = organization_id
              AND om.user_id = public.requesting_user_id()
              AND om.role IN ('owner', 'admin')
        )
    );
CREATE POLICY members_update ON public.organization_members
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.organization_members om
            WHERE om.organization_id = organization_id
              AND om.user_id = public.requesting_user_id()
              AND om.role IN ('owner', 'admin')
        )
    );
CREATE POLICY members_delete ON public.organization_members
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.organization_members om
            WHERE om.organization_id = organization_id
              AND om.user_id = public.requesting_user_id()
              AND om.role IN ('owner', 'admin')
        )
    );

-- Organization Roles
ALTER TABLE public.organization_roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY roles_select ON public.organization_roles
    FOR SELECT
    USING (public.is_org_member(organization_id));
CREATE POLICY roles_insert ON public.organization_roles
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.organization_members om
            WHERE om.organization_id = organization_id
              AND om.user_id = public.requesting_user_id()
              AND om.role = 'owner'
        )
    );
CREATE POLICY roles_update ON public.organization_roles
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.organization_members om
            WHERE om.organization_id = organization_id
              AND om.user_id = public.requesting_user_id()
              AND om.role = 'owner'
        )
    );
CREATE POLICY roles_delete ON public.organization_roles
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.organization_members om
            WHERE om.organization_id = organization_id
              AND om.user_id = public.requesting_user_id()
              AND om.role = 'owner'
        )
    );

-- Invitations
ALTER TABLE public.invitations ENABLE ROW LEVEL SECURITY;
CREATE POLICY invites_select ON public.invitations
    FOR SELECT
    USING (public.is_org_member(organization_id));
CREATE POLICY invites_insert ON public.invitations
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.organization_members om
            WHERE om.organization_id = organization_id
              AND om.user_id = public.requesting_user_id()
              AND om.role IN ('owner', 'admin')
        )
    );
CREATE POLICY invites_update ON public.invitations
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.organization_members om
            WHERE om.organization_id = organization_id
              AND om.user_id = public.requesting_user_id()
              AND om.role IN ('owner', 'admin')
        )
    );
CREATE POLICY invites_delete ON public.invitations
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.organization_members om
            WHERE om.organization_id = organization_id
              AND om.user_id = public.requesting_user_id()
              AND om.role IN ('owner', 'admin')
        )
    );

-- Collections
ALTER TABLE public.collections ENABLE ROW LEVEL SECURITY;
CREATE POLICY collections_select ON public.collections
    FOR SELECT
    USING (public.is_org_member(organization_id));
CREATE POLICY collections_insert ON public.collections
    FOR INSERT
    WITH CHECK (public.is_org_member(organization_id));
CREATE POLICY collections_update ON public.collections
    FOR UPDATE
    USING (public.is_org_member(organization_id));
CREATE POLICY collections_delete ON public.collections
    FOR DELETE
    USING (public.is_org_member(organization_id));

-- Documents
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY documents_select ON public.documents
    FOR SELECT
    USING (public.is_org_member(organization_id));
CREATE POLICY documents_insert ON public.documents
    FOR INSERT
    WITH CHECK (public.is_org_member(organization_id));
CREATE POLICY documents_update ON public.documents
    FOR UPDATE
    USING (public.is_org_member(organization_id));
CREATE POLICY documents_delete ON public.documents
    FOR DELETE
    USING (public.is_org_member(organization_id));

-- Conversation Threads
ALTER TABLE public.conversation_threads ENABLE ROW LEVEL SECURITY;
CREATE POLICY threads_select ON public.conversation_threads
    FOR SELECT
    USING (public.is_org_member(organization_id));
CREATE POLICY threads_insert ON public.conversation_threads
    FOR INSERT
    WITH CHECK (public.is_org_member(organization_id));
CREATE POLICY threads_update ON public.conversation_threads
    FOR UPDATE
    USING (public.is_org_member(organization_id));
CREATE POLICY threads_delete ON public.conversation_threads
    FOR DELETE
    USING (public.is_org_member(organization_id));

-- Conversations
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY conversations_select ON public.conversations
    FOR SELECT
    USING (public.is_org_member(organization_id));
CREATE POLICY conversations_insert ON public.conversations
    FOR INSERT
    WITH CHECK (public.is_org_member(organization_id));
CREATE POLICY conversations_update ON public.conversations
    FOR UPDATE
    USING (public.is_org_member(organization_id));
CREATE POLICY conversations_delete ON public.conversations
    FOR DELETE
    USING (public.is_org_member(organization_id));

-- Audit Logs
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_select ON public.audit_logs
    FOR SELECT
    USING (public.is_org_member(organization_id));

-- 6. Permissions
-- Backend uses service_role key (bypasses RLS). Grants to anon enable RLS enforcement.
GRANT USAGE ON SCHEMA public TO anon, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO anon;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO anon;
