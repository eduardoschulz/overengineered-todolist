"""add_task_fields_to_todo_items

Revision ID: 5a1b2c3d4e5f
Revises: 2693906b62e5
Create Date: 2026-06-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "2693906b62e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("todo_items") as batch_op:
        batch_op.alter_column("todo_list_id", nullable=True)
        batch_op.add_column(sa.Column("description", sa.String(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("status", sa.String(), nullable=False, server_default="pending"))
        batch_op.add_column(sa.Column("assigned_to", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("created_by", sa.String(), nullable=False, server_default="legacy"))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("todo_items") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_by")
        batch_op.drop_column("assigned_to")
        batch_op.drop_column("status")
        batch_op.drop_column("description")
        batch_op.alter_column("todo_list_id", nullable=False)
