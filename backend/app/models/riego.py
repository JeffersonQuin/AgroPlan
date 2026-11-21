"""Sistema de riego: configuración, sectores y red generada.

La red no se dibuja a mano: se genera de forma determinística a partir de los
parámetros del sistema y de los bloques de cultivo. Los goteros no se persisten uno
por uno (serían miles de filas): se derivan de ``red_tramos`` + la separación entre
goteros y los devuelve calculados el endpoint de diseño.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import (
    VALORES_ORIENTACION,
    VALORES_TIPO_NODO,
    VALORES_TIPO_SISTEMA,
    VALORES_TIPO_TRAMO,
    Orientacion,
    TipoSistemaRiego,
)
from app.models.tipos import JSONB_TIPO, check_en


class SistemaRiego(Base):
    """Parámetros de generación del riego. Uno por proyecto."""

    __tablename__ = "sistemas_riego"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    proyecto_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    tipo: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TipoSistemaRiego.GOTEO.value
    )
    fuente_agua: Mapped[str] = mapped_column(String(20), nullable=False)
    tanque_l: Mapped[Decimal | None] = mapped_column(Numeric(8, 1), nullable=True)
    bomba_hp: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False)
    diametro_principal_mm: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=32
    )
    emisor_tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="gotero")
    emisor_caudal_lh: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    separacion_goteros_m: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    separacion_laterales_m: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    orientacion: Mapped[str] = mapped_column(
        String(5), nullable=False, default=Orientacion.ESTE_OESTE.value
    )
    # {"x": 0, "y": 0} en metros, sobre el sistema de coordenadas del terreno
    punto_conexion: Mapped[dict[str, Any]] = mapped_column(JSONB_TIPO, nullable=False)
    num_sectores: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    # Nulo mientras la red no se haya generado: es la señal que bloquea "Continuar".
    red_generada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    parametros_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(check_en("tipo", VALORES_TIPO_SISTEMA), name="ck_sistemas_tipo"),
        CheckConstraint(
            check_en("orientacion", VALORES_ORIENTACION), name="ck_sistemas_orientacion"
        ),
        CheckConstraint("bomba_hp IN (0.5, 1, 1.5, 2)", name="ck_sistemas_bomba_hp"),
        CheckConstraint(
            "emisor_caudal_lh IN (2, 4, 8)", name="ck_sistemas_emisor_caudal"
        ),
        CheckConstraint(
            "separacion_goteros_m >= 0.2 AND separacion_goteros_m <= 1.0",
            name="ck_sistemas_separacion_goteros",
        ),
        CheckConstraint(
            "separacion_laterales_m >= 0.5 AND separacion_laterales_m <= 10",
            name="ck_sistemas_separacion_laterales",
        ),
        CheckConstraint("tanque_l IS NULL OR tanque_l > 0", name="ck_sistemas_tanque"),
        CheckConstraint(
            "num_sectores >= 1 AND num_sectores <= 8", name="ck_sistemas_num_sectores"
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<SistemaRiego {self.id} {self.tipo} sectores={self.num_sectores}>"

    @property
    def emisor(self) -> dict[str, object]:
        """Emisor como objeto anidado del contrato, armado con las columnas planas."""

        return {
            "tipo": self.emisor_tipo,
            "caudal_lh": self.emisor_caudal_lh,
            "separacion_m": self.separacion_goteros_m,
        }


class Sector(Base):
    """Sector de riego: una porción del terreno que se riega en un turno."""

    __tablename__ = "sectores"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sistema_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sistemas_riego.id", ondelete="CASCADE"), nullable=False, index=True
    )
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    etiqueta: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # {"anillo": [[x, y], ...]} en metros
    poligono: Mapped[dict[str, Any]] = mapped_column(JSONB_TIPO, nullable=False)
    area_m2: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    num_goteros: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    caudal_m3h: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    secuencia: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    bloques: Mapped[list["SectorBloque"]] = relationship(back_populates="sector")

    __table_args__ = (
        UniqueConstraint("sistema_id", "numero", name="uq_sectores_sistema_numero"),
        CheckConstraint("numero >= 1", name="ck_sectores_numero"),
        CheckConstraint("area_m2 > 0", name="ck_sectores_area_positiva"),
        CheckConstraint("num_goteros >= 0", name="ck_sectores_goteros_no_negativos"),
        CheckConstraint("caudal_m3h >= 0", name="ck_sectores_caudal_no_negativo"),
        CheckConstraint("secuencia >= 1", name="ck_sectores_secuencia"),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<Sector {self.numero} {self.area_m2} m2>"

    @property
    def cultivo_ids(self) -> list[uuid.UUID]:
        """Ids de los bloques que entran al sector (vía ``sector_bloques``)."""

        return [vinculo.proyecto_cultivo_id for vinculo in getattr(self, "bloques", [])]


class SectorBloque(Base):
    """Reparto de un bloque de cultivo entre sectores.

    Un bloque puede quedar partido entre dos sectores, por eso el vínculo guarda su
    propia superficie y no hay unicidad por ``proyecto_cultivo_id``.
    """

    __tablename__ = "sector_bloques"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sectores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    proyecto_cultivo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("proyecto_cultivos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    area_m2: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sector: Mapped["Sector"] = relationship(back_populates="bloques")

    __table_args__ = (
        UniqueConstraint(
            "sector_id", "proyecto_cultivo_id", name="uq_sector_bloques_vinculo"
        ),
        CheckConstraint("area_m2 > 0", name="ck_sector_bloques_area_positiva"),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<SectorBloque {self.sector_id}->{self.proyecto_cultivo_id} {self.area_m2} m2>"


class RedTramo(Base):
    """Tramo de tubería generado por el motor (principal, secundario, lateral)."""

    __tablename__ = "red_tramos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sistema_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sistemas_riego.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sector_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sectores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tipo: Mapped[str] = mapped_column(String(15), nullable=False)
    diametro_mm: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    longitud_m: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    # {"puntos": [[x, y], ...]} en metros; el front lo pinta como polilínea
    geometria: Mapped[dict[str, Any]] = mapped_column(JSONB_TIPO, nullable=False)
    caudal_m3h: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)

    __table_args__ = (
        CheckConstraint(check_en("tipo", VALORES_TIPO_TRAMO), name="ck_tramos_tipo"),
        CheckConstraint("diametro_mm > 0", name="ck_tramos_diametro"),
        CheckConstraint("longitud_m > 0", name="ck_tramos_longitud_positiva"),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<RedTramo {self.tipo} {self.longitud_m} m>"

    @property
    def puntos(self) -> list[tuple[float, float]]:
        """Polilínea del tramo en metros, lista para pintar."""

        crudo = self.geometria.get("puntos") or [] if self.geometria else []
        return [(float(punto[0]), float(punto[1])) for punto in crudo]


class RedNodo(Base):
    """Componente puntual de la red: tanque, bomba, cabezal, válvula o hidrante."""

    __tablename__ = "red_nodos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sistema_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sistemas_riego.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(15), nullable=False)
    # {"x": 0, "y": 32} en metros
    geometria: Mapped[dict[str, Any]] = mapped_column(JSONB_TIPO, nullable=False)
    tramo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("red_tramos.id", ondelete="SET NULL"), nullable=True
    )
    atributos: Mapped[dict[str, Any] | None] = mapped_column(JSONB_TIPO, nullable=True)

    __table_args__ = (
        CheckConstraint(check_en("tipo", VALORES_TIPO_NODO), name="ck_nodos_tipo"),
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<RedNodo {self.tipo}>"


__all__ = ["RedNodo", "RedTramo", "Sector", "SectorBloque", "SistemaRiego"]
