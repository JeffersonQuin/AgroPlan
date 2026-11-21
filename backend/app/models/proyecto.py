"""Proyecto agrícola y su terreno.

Un proyecto pertenece a un único usuario (``usuario_id``) y agrupa terreno,
cultivos asignados, sistema de riego y las corridas del agente. La geometría del
terreno es la única fuente de verdad: ``area_m2``, ``perimetro_m`` y ``lados`` se
derivan de ``geometria`` y los escribe el backend, nunca el cliente.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import (
    VALORES_ESTADO_PROYECTO,
    VALORES_FORMA_TERRENO,
    VALORES_FUENTE_AGUA,
    VALORES_ORIGEN_CAUDAL,
    VALORES_UNIDAD,
    EstadoProyecto,
    OrigenCaudal,
    UnidadSistema,
)
from app.models.tipos import JSONB_TIPO, check_en


class Proyecto(Base):
    """Raíz de todo el dominio: el contenedor de un diseño agrícola."""

    __tablename__ = "proyectos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    zona: Mapped[str | None] = mapped_column(String(120), nullable=True)
    unidad: Mapped[str] = mapped_column(
        String(10), nullable=False, default=UnidadSistema.METRICO.value
    )
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EstadoProyecto.EN_PROGRESO.value
    )
    paso_actual: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    ultimo_paso_completado: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Referencia lógica a ``agente_corridas.id`` sin FK física: la tabla de corridas
    # referencia a ``proyectos`` y una FK mutua obliga a un ALTER que SQLite no
    # soporta. La integridad la garantiza el servicio que aplica la corrida.
    corrida_actual_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    eliminado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    __table_args__ = (
        CheckConstraint(check_en("unidad", VALORES_UNIDAD), name="ck_proyectos_unidad"),
        CheckConstraint(check_en("estado", VALORES_ESTADO_PROYECTO), name="ck_proyectos_estado"),
        CheckConstraint("paso_actual BETWEEN 1 AND 4", name="ck_proyectos_paso_actual"),
        CheckConstraint(
            "ultimo_paso_completado BETWEEN 0 AND 4", name="ck_proyectos_ultimo_paso"
        ),
        CheckConstraint("version >= 1", name="ck_proyectos_version"),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<Proyecto {self.id} {self.nombre!r}>"


class Terreno(Base):
    """Forma, suelo y agua disponible de la parcela. Uno por proyecto."""

    __tablename__ = "terrenos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    proyecto_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    nombre_parcela: Mapped[str] = mapped_column(String(60), nullable=False)
    forma: Mapped[str] = mapped_column(String(20), nullable=False)
    # {"vertices": [{"x": 0, "y": 0}], "cerrado": true, "unidad": "m", "eje_y": "norte"}
    geometria: Mapped[dict[str, Any]] = mapped_column(JSONB_TIPO, nullable=False)
    area_m2: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    perimetro_m: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    lados: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    suelo_codigo: Mapped[str] = mapped_column(
        ForeignKey("suelos.codigo"), nullable=False, index=True
    )
    pendiente_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal(0)
    )
    fuente_agua: Mapped[str] = mapped_column(String(20), nullable=False)
    # Caudal que informó el cliente. Nulo significa "no lo informó": en ese caso el
    # sistema asigna uno según ``caudal_base_fuente``.
    caudal_disponible_m3h: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    # Caudal que usa todo el sistema (paso 3, agente, cómputo y PDF). Nunca es nulo:
    # por eso ningún consumidor necesita preguntarse si hay caudal.
    caudal_efectivo_m3h: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    # Profundidad del nivel dinámico del pozo (paso 1). Opcional: no cambia ningún
    # cálculo hidráulico, se informa para el cómputo de la bomba.
    profundidad_nivel_dinamico_m: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    caudal_origen: Mapped[str] = mapped_column(
        String(10), nullable=False, default=OrigenCaudal.ASUMIDO.value
    )
    # Fuente con la que se asumió el caudal. Permite detectar que el usuario cambió
    # ``fuente_agua`` y el valor asumido quedó viejo.
    caudal_base_fuente: Mapped[str | None] = mapped_column(String(20), nullable=True)
    caudal_actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(check_en("forma", VALORES_FORMA_TERRENO), name="ck_terrenos_forma"),
        CheckConstraint(
            check_en("fuente_agua", VALORES_FUENTE_AGUA), name="ck_terrenos_fuente_agua"
        ),
        CheckConstraint(
            check_en("caudal_origen", VALORES_ORIGEN_CAUDAL), name="ck_terrenos_caudal_origen"
        ),
        CheckConstraint("area_m2 > 0", name="ck_terrenos_area_positiva"),
        CheckConstraint("perimetro_m > 0", name="ck_terrenos_perimetro_positivo"),
        CheckConstraint("lados >= 3", name="ck_terrenos_lados_minimos"),
        CheckConstraint(
            "pendiente_pct >= 0 AND pendiente_pct <= 30", name="ck_terrenos_pendiente"
        ),
        CheckConstraint("caudal_efectivo_m3h > 0", name="ck_terrenos_caudal_positivo"),
        CheckConstraint(
            "caudal_disponible_m3h IS NULL OR caudal_disponible_m3h > 0",
            name="ck_terrenos_caudal_cliente_positivo",
        ),
        # Invariante del caudal: o lo puso el cliente, o lo asumió el sistema con una
        # fuente registrada. Nunca las dos cosas ni ninguna.
        CheckConstraint(
            "(caudal_origen = 'cliente' AND caudal_disponible_m3h IS NOT NULL"
            " AND caudal_base_fuente IS NULL)"
            " OR (caudal_origen = 'asumido' AND caudal_disponible_m3h IS NULL"
            " AND caudal_base_fuente IS NOT NULL)",
            name="ck_terrenos_caudal_coherente",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<Terreno {self.id} fuente={self.fuente_agua} caudal={self.caudal_efectivo_m3h}>"


__all__ = ["Proyecto", "Terreno"]
