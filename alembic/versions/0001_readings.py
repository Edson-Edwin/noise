"""Initial readings schema."""
from alembic import op
import sqlalchemy as sa
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("readings",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("device_id", sa.String(48), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("noise_score", sa.Integer(), nullable=False),
        sa.Column("noisy", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("noise_score BETWEEN 0 AND 4095", name="valid_score"),
        sa.UniqueConstraint("device_id", "event_id", name="uq_device_event"))
    op.create_index("ix_readings_created_at", "readings", ["created_at"])

def downgrade():
    op.drop_table("readings")
