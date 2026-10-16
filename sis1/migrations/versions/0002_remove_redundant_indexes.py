"""Use the post prefix of the unique indexes for post lookups."""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_likes_post_id", table_name="likes")
    op.drop_index("ix_views_post_id", table_name="views")


def downgrade():
    op.create_index("ix_likes_post_id", "likes", ["post_id"])
    op.create_index("ix_views_post_id", "views", ["post_id"])
