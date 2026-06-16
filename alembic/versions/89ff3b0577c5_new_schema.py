"""Multi-tenant schema: organizations, fixed UUIDs, simplified RBAC

Revision ID: 89ff3b0577c5
Revises: 0faf4e09476d
Create Date: 2026-06-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "89ff3b0577c5"
down_revision: Union[str, Sequence[str], None] = "0faf4e09476d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- New tables ---

    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)

    op.create_table(
        "organization_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(32), server_default="member", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
    )

    op.create_table(
        "invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("token", sa.String(128), nullable=False),
        sa.Column("role", sa.String(32), server_default="member", nullable=False),
        sa.Column("invited_by_id", sa.UUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invitations_token"), "invitations", ["token"], unique=True)

    op.create_table(
        "collections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("feedback_score", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Alter existing tables ---

    # Add organization-scoped columns to documents
    op.add_column("documents", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("documents", sa.Column("collection_id", sa.UUID(), nullable=True))
    op.add_column("documents", sa.Column("uploaded_by_id", sa.UUID(), nullable=True))
    op.add_column("documents", sa.Column("chunk_count", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("documents", sa.Column("is_public_in_org", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.create_foreign_key(None, "documents", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key(None, "documents", "collections", ["collection_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(None, "documents", "users", ["uploaded_by_id"], ["id"], ondelete="CASCADE")
    op.create_index(op.f("ix_documents_organization_id"), "documents", ["organization_id"], unique=False)

    # Drop old columns from documents
    op.drop_column("documents", "doc_metadata")
    # owner_id will be migrated to uploaded_by_id in backfill
    # is_public remains as-is during transition

    # Add org-scoped columns to audit_logs
    op.add_column("audit_logs", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("audit_logs", sa.Column("actor_id", sa.UUID(), nullable=True))
    op.create_foreign_key(None, "audit_logs", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(None, "audit_logs", "users", ["actor_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_audit_logs_organization_id"), "audit_logs", ["organization_id"], unique=False)


def downgrade() -> None:
    op.drop_table("conversations")
    op.drop_table("collections")
    op.drop_table("invitations")
    op.drop_table("organization_members")
    op.drop_table("organizations")

    op.drop_index(op.f("ix_documents_organization_id"), table_name="documents")
    op.drop_column("documents", "is_public_in_org")
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "uploaded_by_id")
    op.drop_column("documents", "collection_id")
    op.drop_column("documents", "organization_id")
    op.add_column("documents", sa.Column("doc_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.drop_index(op.f("ix_audit_logs_organization_id"), table_name="audit_logs")
    op.drop_column("audit_logs", "actor_id")
    op.drop_column("audit_logs", "organization_id")
