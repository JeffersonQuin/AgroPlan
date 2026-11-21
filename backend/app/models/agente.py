"""Corridas del agente de recomendaciones: snapshot inmutable por ejecución.

Cada corrida guarda su entrada exacta, su salida congelada, la versión del motor y
del prompt, y las fuentes citadas. Sin eso no se puede explicar (ni reproducir) por
qué el agente recomendó lo que recomendó.

El agente corre contra un gateway OpenAI-compatible y usa búsqueda web en vivo como
herramienta: por eso el modelo se guarda por corrida y las fuentes son obligatorias.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import (
    VALORES_ESTADO_CORRIDA,
    VALORES_TIPO_FUENTE_AGENTE,
    VALORES_TIPO_RECOMENDACION,
    EstadoCorrida,
)
from app.models.tipos import JSONB_TIPO, check_en


class AgenteCorrida(Base):
    """Una ejecución del agente para un proyecto."""

    __tablename__ = "agente_corridas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    proyecto_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    estado: Mapped[str] = mapped_column(
        String(15), nullable=False, default=EstadoCorrida.PENDIENTE.value
    )
    # Payload exacto con el que se ejecutó: productos, área, suelo, fuente de agua,
    # caudal efectivo (con su origen), zona y pendiente.
    entrada: Mapped[dict[str, Any]] = mapped_column(JSONB_TIPO, nullable=False)
    # Salida congelada: cultivos recomendados, parámetros de riego, advertencias y
    # supuestos. La geometría (bloques, sectores, red) no se guarda acá: la calcula el
    # motor determinístico y vive en sus propias tablas.
    salida: Mapped[dict[str, Any] | None] = mapped_column(JSONB_TIPO, nullable=True)
    # SHA-256 del intake normalizado: permite saber si la corrida vigente quedó
    # desactualizada porque el usuario cambió productos, área o suelo, sin re-ejecutar
    # el agente para averiguarlo.
    intake_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    modelo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    motor_version: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    tokens_entrada: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_salida: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duracion_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    iniciado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    terminado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(check_en("estado", VALORES_ESTADO_CORRIDA), name="ck_corridas_estado"),
        CheckConstraint(
            "duracion_ms IS NULL OR duracion_ms >= 0", name="ck_corridas_duracion"
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<AgenteCorrida {self.id} {self.estado}>"


class AgenteRecomendacion(Base):
    """Recomendación puntual del agente, aplicable o no al proyecto."""

    __tablename__ = "agente_recomendaciones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    corrida_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agente_corridas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB_TIPO, nullable=False)
    justificacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    confianza: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    aplicada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    aplicada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            check_en("tipo", VALORES_TIPO_RECOMENDACION), name="ck_recomendaciones_tipo"
        ),
        CheckConstraint(
            "confianza IS NULL OR (confianza >= 0 AND confianza <= 1)",
            name="ck_recomendaciones_confianza",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<AgenteRecomendacion {self.tipo} aplicada={self.aplicada}>"


class AgenteFuente(Base):
    """Fuente citada por el agente: procedencia de una recomendación."""

    __tablename__ = "agente_fuentes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    corrida_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agente_corridas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(15), nullable=False)
    titulo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    fragmento: Mapped[str | None] = mapped_column(Text, nullable=True)
    recuperado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(check_en("tipo", VALORES_TIPO_FUENTE_AGENTE), name="ck_fuentes_tipo"),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<AgenteFuente {self.tipo} {self.titulo!r}>"


__all__ = ["AgenteCorrida", "AgenteFuente", "AgenteRecomendacion"]
