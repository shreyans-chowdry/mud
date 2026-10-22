"""Persist per-order transition order independently of same-second wall-clock ties."""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('transition_sequence', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('order_transitions', sa.Column('sequence', sa.Integer(), nullable=True))
    # Legacy second-resolution timestamps cannot establish chronology within a tie.
    # Keep those sequences NULL; allocate new counters after all legacy records.
    op.execute('UPDATE orders SET transition_sequence = (SELECT COUNT(*) FROM order_transitions WHERE order_transitions.order_id = orders.id)')


def downgrade():
    op.drop_column('order_transitions', 'sequence')
    op.drop_column('orders', 'transition_sequence')
