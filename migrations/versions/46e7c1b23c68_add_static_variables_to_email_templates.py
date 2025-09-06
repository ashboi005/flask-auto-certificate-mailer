"""Add static variables to email templates

Revision ID: 46e7c1b23c68
Revises: 364c8433b332
Create Date: 2025-09-06 17:36:48.049332

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '46e7c1b23c68'
down_revision = '364c8433b332'
branch_labels = None
depends_on = None


def upgrade():
    # Add static_variables column to email_template table
    op.add_column('email_template', sa.Column('static_variables', sa.Text(), nullable=True))


def downgrade():
    # Remove static_variables column from email_template table
    op.drop_column('email_template', 'static_variables')
