"""add task actions table

Revision ID: 002
Revises: 001
Create Date: 2026-01-22 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create task_actions table
    op.create_table(
        'task_actions',
        sa.Column('action_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='proposed'),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('dry_run', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approved_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('action_id')
    )

    # Create indexes for efficient querying
    op.create_index('ix_task_actions_task_id', 'task_actions', ['task_id'])
    op.create_index('ix_task_actions_status', 'task_actions', ['status'])
    op.create_index('ix_task_actions_action_type', 'task_actions', ['action_type'])
    op.create_index('ix_task_actions_created_at', 'task_actions', ['created_at'])

    # Add foreign key constraint to tasks table
    op.create_foreign_key(
        'fk_task_actions_task_id',
        'task_actions', 'tasks',
        ['task_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Drop foreign key
    op.drop_constraint('fk_task_actions_task_id', 'task_actions', type_='foreignkey')

    # Drop indexes
    op.drop_index('ix_task_actions_created_at', 'task_actions')
    op.drop_index('ix_task_actions_action_type', 'task_actions')
    op.drop_index('ix_task_actions_status', 'task_actions')
    op.drop_index('ix_task_actions_task_id', 'task_actions')

    # Drop table
    op.drop_table('task_actions')
