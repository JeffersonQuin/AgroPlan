from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RolUsuario(StrEnum):
    ADMIN = "admin"
    USUARIO = "usuario"
    CLIENTE = "cliente"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    google_sub: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email_verificado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    nombre: Mapped[str | None] = mapped_column(String(150), nullable=True)
    foto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rol: Mapped[str] = mapped_column(String(30), nullable=False, default=RolUsuario.USUARIO.value)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    ultimo_acceso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
