from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    companies: Mapped[list["Company"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    kb_profiles: Mapped[list["KbProfile"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )