"""Contratos del sistema de riego: configuración, sectores, preview y red.

La red y los sectores los genera el backend; el cliente solo manda los parámetros de
generación y su distribución de cultivos en sectores. Ningún área ni caudal se
acepta como entrada: se derivan de la geometría y de los parámetros.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FuenteAgua, Orientacion, TipoNodo, TipoSistemaRiego, TipoTramo
from app.schemas.comun import Advertencia, Poligono, Punto


class EmisorIn(BaseModel):
    """Emisor del sistema. En el MVP solo goteo."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["gotero"] = "gotero"
    caudal_lh: Literal[2, 4, 8] = 2
    separacion_m: float = Field(default=0.2, ge=0.2, le=1.0)


class SistemaRiegoIn(BaseModel):
    """Parámetros de generación del paso 3.

    ``fuente_agua`` debe coincidir con la del terreno: si no, 422.
    """

    model_config = ConfigDict(extra="forbid")

    tipo: TipoSistemaRiego = TipoSistemaRiego.GOTEO
    fuente_agua: FuenteAgua
    tanque_l: float | None = Field(default=None, gt=0, le=1000000)
    bomba_hp: Literal[0.5, 1, 1.5, 2] = 1
    diametro_principal_mm: Literal[32, 40, 50] = 32
    emisor: EmisorIn = Field(default_factory=EmisorIn)
    separacion_laterales_m: float = Field(default=5, ge=0.5, le=10)
    orientacion: Orientacion = Orientacion.ESTE_OESTE
    punto_conexion: Punto
    num_sectores: int = Field(default=1, ge=1, le=8)


class SistemaRiegoOut(BaseModel):
    """Configuración persistida con su estado de generación."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: TipoSistemaRiego
    fuente_agua: FuenteAgua
    tanque_l: float | None = None
    bomba_hp: float
    diametro_principal_mm: int
    emisor: EmisorIn
    separacion_laterales_m: float
    orientacion: Orientacion
    punto_conexion: Punto
    num_sectores: int
    red_generada_en: datetime | None = None
    parametros_version: int


class SectorIn(BaseModel):
    """Un sector del modal 3.1: qué bloques entran y en qué turno."""

    model_config = ConfigDict(extra="forbid")

    numero: int = Field(ge=1, le=8)
    etiqueta: str | None = Field(default=None, max_length=60)
    cultivo_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    area_m2: float = Field(gt=0)
    secuencia: int = Field(ge=1, le=8)


class SectoresIn(BaseModel):
    """Reemplazo completo de los sectores: "Aplicar y generar" del modal."""

    model_config = ConfigDict(extra="forbid")

    sectores: list[SectorIn] = Field(min_length=1, max_length=8)


class SectorUpdate(BaseModel):
    """Edición parcial de un sector ya generado."""

    model_config = ConfigDict(extra="forbid")

    etiqueta: str | None = Field(default=None, max_length=60)
    secuencia: int | None = Field(default=None, ge=1, le=8)


class SectorOut(BaseModel):
    """Sector generado, con sus derivados hidráulicos."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero: int
    etiqueta: str | None = None
    poligono: Poligono
    area_m2: float
    num_goteros: int
    caudal_m3h: float
    secuencia: int
    cultivo_ids: list[uuid.UUID] = Field(default_factory=list)


class SectorBloqueIn(BaseModel):
    """Alta de un bloque de cultivo dentro de un sector."""

    model_config = ConfigDict(extra="forbid")

    proyecto_cultivo_id: uuid.UUID
    area_m2: float = Field(gt=0)


class SectorBloqueOut(BaseModel):
    """Vínculo persistido entre un sector y un bloque de cultivo."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sector_id: uuid.UUID
    proyecto_cultivo_id: uuid.UUID
    area_m2: float


class TramoOut(BaseModel):
    """Tramo de tubería ya trazado, listo para pintar."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sector_id: uuid.UUID | None = None
    tipo: TipoTramo
    diametro_mm: int
    longitud_m: float
    caudal_m3h: float | None = None
    orden: int
    puntos: list[tuple[float, float]]


class NodoOut(BaseModel):
    """Nodo puntual de la red: tanque, bomba, cabezal, válvula o hidrante."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: TipoNodo
    geometria: Punto
    tramo_id: uuid.UUID | None = None
    atributos: dict | None = None


class EmisoresTramoOut(BaseModel):
    """Goteros de un lateral, ya posicionados.

    No viven en la base: se derivan de ``longitud`` y de la separación entre goteros.
    """

    tramo_id: uuid.UUID
    separacion_m: float
    puntos: list[tuple[float, float]] = Field(default_factory=list)


class ComputoOut(BaseModel):
    """Cómputo rápido de materiales, derivado de la red.

    El motor solo computa estos tres rubros. Tanque, bomba y conexiones no se
    calculan y no se contrastan contra la propuesta del agente (S3).
    """
    tuberia_m: float
    goteros_u: int
    valvulas_u: int


class RedOut(BaseModel):
    """Red completa de un proyecto, tal como la pinta el canvas."""

    nodos: list[NodoOut] = Field(default_factory=list)
    tramos: list[TramoOut] = Field(default_factory=list)
    emisores: list[EmisoresTramoOut] = Field(default_factory=list)


class PreviewOut(BaseModel):
    """Panel derecho del paso 3, antes de generar la red.

    Devuelve el caudal **efectivo** del terreno (informado o asumido) junto con los
    supuestos usados, para que el front pueda mostrarlos como "estimado".
    """

    caudal_efectivo_m3h: float
    caudal_origen: str
    caudal_sector_m3h: float
    caudal_total_m3h: float
    presion_bar: float
    tiempo_riego_min: int
    autonomia_dias: float | None = None
    computo: ComputoOut
    advertencias: list[Advertencia] = Field(default_factory=list)


class DisenoOut(BaseModel):
    """Resultado completo de una generación: lo que consume el paso 4 y el PDF."""

    sistema: SistemaRiegoOut
    sectores: list[SectorOut] = Field(default_factory=list)
    red: RedOut = Field(default_factory=RedOut)
    computo: ComputoOut
    advertencias: list[Advertencia] = Field(default_factory=list)
