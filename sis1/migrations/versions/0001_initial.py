from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "posts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("content", sa.Text(), nullable=True),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(128), nullable=False, unique=True),
    )
    for table in ("likes", "views"):
        op.create_table(
            table,
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("post_id", sa.BigInteger(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
            sa.UniqueConstraint("post_id", "user_id", name=f"uq_{table}_post_user"),
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])
        op.create_index(f"ix_{table}_post_id", table, ["post_id"])
    op.create_table(
        "post_counters",
        sa.Column("post_id", sa.BigInteger(), sa.ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("stripe", sa.Integer(), primary_key=True),
        sa.Column("likes_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("views_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.CheckConstraint("stripe >= 0 AND stripe < 16", name="ck_counter_stripe"),
        sa.CheckConstraint("likes_count >= 0 AND views_count >= 0", name="ck_counter_positive"),
    )


def downgrade():
    op.drop_table("post_counters")
    op.drop_table("views")
    op.drop_table("likes")
    op.drop_table("users")
    op.drop_table("posts")
