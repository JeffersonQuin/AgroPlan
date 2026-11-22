"""Precios de materiales investigados por el agente, compartidos entre usuarios.

El agente busca precios con fuentes web para el cómputo del informe (S6). Guardar lo
que encontró evita que cada corrida de cada usuario vuelva a investigar lo mismo y
gaste tokens: la próxima corrida reutiliza el precio y su fuente mientras el dato
siga vigente.

Hay **una fila por material**, no una por corrida: ``clave`` es la identidad
normalizada (rubro + descripción + unidad) y el upsert actualiza la misma fila cuando
el precio se vuelve a investigar. ``recuperado_en`` es cuándo se obtuvo el precio y
``actualizado_en`` cuándo se escribió por última vez: la vigencia se decide por la
primera, no por la segunda.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MaterialPrecio(Base):
    """Precio unitario de un material, con su fuente y su fecha de recuperación."""

    __tablename__ = "materiales_precio"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Identidad normalizada del material: minúsculas, sin tildes, espacios colapsados.
    # Es lo que permite reconocer el mismo material en la corrida de otro usuario.
    clave: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    rubro: Mapped[str] = mapped_column(String(60), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    unidad: Mapped[str] = mapped_column(String(20), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="BOB")
    precio_unitario_bs: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False
    )
    fuente_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Cuándo se obtuvo el precio: es la fecha que decide si sigue vigente.
    recuperado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "precio_unitario_bs > 0", name="ck_materiales_precio_positivo"
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<MaterialPrecio {self.rubro!r} {self.precio_unitario_bs}>"


__all__ = ["MaterialPrecio"]
