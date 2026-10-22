"""Deduplicate local business entitlements across canonical re-inclusion notifications."""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('entitlements',
        sa.Column('order_id', sa.String(36), primary_key=True),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('source_key', sa.String(200), nullable=False),
        sa.Column('tx_hash', sa.String(66), nullable=True),
        sa.Column('block_hash', sa.String(66), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False))


def downgrade():
    op.drop_table('entitlements')
