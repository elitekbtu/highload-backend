from __future__ import annotations

from typing import TYPE_CHECKING


from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, ID_TYPE

if TYPE_CHECKING:
    from models import Like, View


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)

    username: Mapped[str] = mapped_column(String(128), unique=True)

    views: Mapped[list[View]] = relationship(
        "View",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    likes: Mapped[list[Like]] = relationship(
        "Like",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
