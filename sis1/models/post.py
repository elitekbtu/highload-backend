from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models import Like, View


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    views: Mapped[list[View]] = relationship(
        "View",
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    likes: Mapped[list[Like]] = relationship(
        "Like",
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
