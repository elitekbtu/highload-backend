from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, ID_TYPE

if TYPE_CHECKING:
    from models import Post, User


class View(Base):
    __tablename__ = "views"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_views_post_user"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
    )

    post: Mapped[Post] = relationship(
        "Post",
        back_populates="views",
    )
    user: Mapped[User] = relationship(
        "User",
        back_populates="views",
    )
