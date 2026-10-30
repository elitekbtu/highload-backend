from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class PostCounter(Base):
    __tablename__ = "post_counters"

    post_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    likes_count: Mapped[int] = mapped_column(BigInteger, server_default="0")
    views_count: Mapped[int] = mapped_column(BigInteger, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
