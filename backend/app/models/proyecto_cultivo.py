"""Bloques de cultivo asignados dentro del terreno de un proyecto.

Un cultivo puede ocupar más de un bloque (dos lotes de papa, por ejemplo): por eso
no hay restricción de unicidad sobre ``cultivo_codigo`` y sí un ``orden``.
``area_m2`` se deriva del polígono y lo escribe el backend; el cliente puede editar
el polígono, nunca el área.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import VALORES_ORIGEN_BLOQUE, OrigenBloque
from app.models.tipos import JSONB_TIPO, check_en


class ProyectoCultivo(Base):
    """Un bloque de cultivo: geometría, fechas y demanda hídrica."""

    __tablename__ = "proyecto_cultivos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    proyecto_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cultivo_codigo: Mapped[str] = mapped_column(
        ForeignKey("cultivos.codigo"), nullable=False, index=True
    )
    etiqueta: Mapped[str | None] = mapped_column(String(60), nullable=True)
    area_m2: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # {"anillo": [[x, y], ...]} en metros, mismo sistema de coordenadas del terreno
    poligono: Mapped[dict[str, Any]] = mapped_column(JSONB_TIPO, nullable=False)
    siembra: Mapped[date | None] = mapped_column(Date, nullable=True)
    cosecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    demanda_l_m2_dia: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    origen: Mapped[str] = mapped_column(
        String(10), nullable=False, default=OrigenBloque.MANUAL.value
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(check_en("origen", VALORES_ORIGEN_BLOQUE), name="ck_bloques_origen"),
        CheckConstraint("area_m2 > 0", name="ck_bloques_area_positiva"),
        CheckConstraint("demanda_l_m2_dia >= 0", name="ck_bloques_demanda_no_negativa"),
        CheckConstraint("orden >= 1", name="ck_bloques_orden"),
        CheckConstraint(
            "siembra IS NULL OR cosecha IS NULL OR cosecha > siembra",
            name="ck_bloques_cosecha_posterior",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<ProyectoCultivo {self.cultivo_codigo} {self.area_m2} m2>"


__all__ = ["ProyectoCultivo"]
