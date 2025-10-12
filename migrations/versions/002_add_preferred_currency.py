"""Add preferred_currency to users

Revision ID: 002_preferred_currency
Revises: 001_initial
Create Date: 2025-10-12 12:55:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '002_preferred_currency'
down_revision = '001_initial'
branch_labels = None
depends_on = None

def upgrade():
    # Add preferred_currency column to users table
    op.add_column('users', sa.Column('preferred_currency', sa.String(length=3), nullable=True))

def downgrade():
    # Remove preferred_currency column
    op.drop_column('users', 'preferred_currency')