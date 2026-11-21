"""Catálogos del producto.

Son tablas de referencia sembradas por la migración inicial del dominio: no tienen
CRUD en la API. Sin ``cultivos`` no existe el cálculo de demanda hídrica del paso 4,
y sin ``suelos`` el motor no puede decidir la separación entre goteros.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import VALORES_ORIGEN_CULTIVO, OrigenCultivo
from app.models.tipos import JSONB_TIPO, check_en


class Cultivo(Base):
    """Ficha agronómica de un cultivo del catálogo mínimo (5 a 8 filas)."""

    __tablename__ = "cultivos"

    codigo: Mapped[str] = mapped_column(String(30), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    icono: Mapped[str] = mapped_column(String(8), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    demanda_agua_l_m2_dia: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    demanda_agua_l_planta_dia: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    ciclo_dias: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    densidad_plantas_m2: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    profundidad_raiz_cm: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    meses_siembra: Mapped[list[int] | None] = mapped_column(JSONB_TIPO, nullable=True)
    # Coeficiente de cultivo (Kc pico) del paso 2. Sale de la ficha curada o de la
    # investigación; nunca lo inventa el motor.
    kc: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    # {"franco": {"veredicto": "apto", "motivo": "drenaje y retención equilibrados"}}
    aptitud_suelo: Mapped[dict[str, Any] | None] = mapped_column(JSONB_TIPO, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # ``agente`` cuando la ficha la creó el agente investigando un producto que no
    # existía: se usa en el acto y queda pendiente de revisión con sus fuentes.
    origen: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=OrigenCultivo.HUMANO.value,
        server_default=OrigenCultivo.HUMANO.value,
    )
    revisado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fuentes: Mapped[list[dict] | None] = mapped_column(JSONB_TIPO, nullable=True)

    __table_args__ = (
        CheckConstraint("demanda_agua_l_m2_dia > 0", name="ck_cultivos_demanda_positiva"),
        CheckConstraint("ciclo_dias > 0", name="ck_cultivos_ciclo_positivo"),
        CheckConstraint(
            check_en("origen", VALORES_ORIGEN_CULTIVO), name="ck_cultivos_origen"
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<Cultivo {self.codigo}>"


class Suelo(Base):
    """Tipo de suelo del terreno: define infiltración y retención de agua."""

    __tablename__ = "suelos"

    codigo: Mapped[str] = mapped_column(String(20), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), nullable=False)
    infiltracion_mm_h: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    retencion_agua_mm_m: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)

    __table_args__ = (
        CheckConstraint("infiltracion_mm_h > 0", name="ck_suelos_infiltracion_positiva"),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<Suelo {self.codigo}>"
