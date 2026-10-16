from sqlalchemy import BigInteger, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base

COUNTER_STRIPES = 16


class PostCounter(Base):
    __tablename__ = "post_counters"
    __table_args__ = (
        CheckConstraint("stripe >= 0 AND stripe < 16", name="ck_counter_stripe"),
        CheckConstraint("likes_count >= 0 AND views_count >= 0", name="ck_counter_positive"),
    )

    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    stripe: Mapped[int] = mapped_column(primary_key=True)
    likes_count: Mapped[int] = mapped_column(BigInteger, server_default="0")
    views_count: Mapped[int] = mapped_column(BigInteger, server_default="0")
