"""Contrato del agente de recomendaciones y del diseño que produce el motor.

``PropuestaAgente`` es el ``response_model`` del agente: **no contiene geometría**.
El agente elige cultivos y justifica; el motor determinístico calcula polígonos,
sectores, red y cómputo. Un LLM que devuelve coordenadas devuelve ficción.
"""

import hashlib
import json
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    EstadoProyecto,
    FuenteAgua,
    OrigenCaudal,
    TipoFuenteAgente,
    TipoRecomendacion,
)
from app.schemas.comun import Advertencia, Poligono, Punto
from app.schemas.riego import ComputoOut, RedOut, SectorOut, SistemaRiegoOut

# --------------------------------------------------------------------------- #
# Entrada del agente
# --------------------------------------------------------------------------- #


class ProductoDeseado(BaseModel):
    """Un producto que el cliente quiere sembrar."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=2, max_length=60)
    prioridad: int = Field(default=1, ge=1, le=9)
    area_deseada_m2: float | None = Field(default=None, gt=0)


class EntradaAgente(BaseModel):
    """Lo mínimo que necesita el agente para recomendar.

    Obligatorio: productos, área, suelo, fuente de agua, caudal efectivo y zona. El
    caudal llega siempre resuelto por el backend: si el cliente no lo informó, el
    sistema ya le asignó uno y lo marca como ``asumido``.
    """

    model_config = ConfigDict(extra="forbid")

    proyecto_id: uuid.UUID
    productos: list[ProductoDeseado] = Field(min_length=1, max_length=8)
    area_m2: float = Field(gt=0)
    suelo_codigo: str = Field(min_length=2, max_length=20)
    fuente_agua: FuenteAgua
    caudal_efectivo_m3h: float = Field(gt=0, le=50)
    caudal_origen: OrigenCaudal
    zona: str | None = Field(default=None, max_length=120)
    pendiente_pct: float = Field(default=0, ge=0, le=30)
    # Día en que el usuario siembra: el agente devuelve la cosecha a partir de este
    # dato y del ciclo que investiga. Opcional para no invalidar corridas viejas.
    siembra: date | None = None

    def huella(self) -> str:
        """SHA-256 canónico del intake, para ``agente_corridas.intake_hash``.

        Si el usuario cambia productos, área, suelo, caudal o zona, la huella cambia y
        la corrida vigente queda marcada como desactualizada sin volver a ejecutar el
        agente.
        """

        payload = self.model_dump(mode="json", exclude_none=True)
        normalizado = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Salida del agente (sin geometría)
# --------------------------------------------------------------------------- #


class CultivoRecomendado(BaseModel):
    """Cultivo elegido por el agente con su justificación y sus fuentes."""

    model_config = ConfigDict(extra="forbid")

    cultivo_codigo: str = Field(min_length=2, max_length=30)
    nombre: str = Field(min_length=2, max_length=60)
    color: str | None = Field(default=None, max_length=7)
    # Asignación propuesta, no geometría: el motor la convierte en polígonos y el área
    # derivada de esa geometría es la autoritativa. Nunca es un resultado calculado.
    area_m2: float = Field(gt=0)
    demanda_l_m2_dia: float = Field(ge=0, le=20)
    ciclo_dias: int | None = Field(default=None, ge=1, le=730)
    siembra_sugerida: date | None = None
    cosecha_sugerida: date | None = None
    justificacion: str = Field(max_length=600)
    # Índices 1-based sobre las fuentes recuperadas en la corrida, no ids inventados
    # por el modelo.
    fuente_ids: list[int] = Field(default_factory=list)


class EmisorRecomendado(BaseModel):
    """Emisor y separaciones que recomienda el agente."""

    model_config = ConfigDict(extra="forbid")

    tipo: str = Field(default="gotero", max_length=20)
    caudal_lh: float = Field(gt=0, le=20)
    separacion_m: float = Field(gt=0, le=2)


class SistemaRecomendado(BaseModel):
    """Parámetros de riego recomendados. El motor los convierte en red."""

    model_config = ConfigDict(extra="forbid")

    tipo: str = Field(default="goteo", max_length=20)
    emisor: EmisorRecomendado
    separacion_laterales_m: float = Field(gt=0, le=10)
    tanque_l: float | None = Field(default=None, gt=0)
    bomba_hp: float = Field(gt=0, le=10)
    num_sectores: int = Field(default=1, ge=1, le=8)


class PropuestaAgente(BaseModel):
    """``response_model`` del agente: cultivos + parámetros, nunca geometría.

    El campo ``fuentes`` no lo llena el modelo: lo llena el backend a partir de las
    herramientas de búsqueda que efectivamente se ejecutaron en la corrida.
    """

    model_config = ConfigDict(extra="forbid")

    cultivos: list[CultivoRecomendado] = Field(min_length=1, max_length=8)
    sistema: SistemaRecomendado
    advertencias: list[Advertencia] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Geometría generada por el motor
# --------------------------------------------------------------------------- #


class BloqueGenerado(BaseModel):
    """Bloque de cultivo con su polígono listo para pintar."""

    id: uuid.UUID
    cultivo_codigo: str
    color: str
    poligono: Poligono
    area_m2: float
    centroide: Punto


class DisenoGenerado(BaseModel):
    """Salida completa del motor: lo que el front pinta y el PDF consume."""

    bloques: list[BloqueGenerado] = Field(default_factory=list)
    sistema: SistemaRiegoOut
    sectores: list[SectorOut] = Field(default_factory=list)
    red: RedOut = Field(default_factory=RedOut)
    computo: ComputoOut
    advertencias: list[Advertencia] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Corridas
# --------------------------------------------------------------------------- #


class FuenteOut(BaseModel):
    """Fuente citada por el agente."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: TipoFuenteAgente
    titulo: str | None = None
    url: str | None = None
    fragmento: str | None = None
    recuperado_en: datetime


class RecomendacionOut(BaseModel):
    """Recomendación emitida por el agente para una corrida."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    corrida_id: uuid.UUID
    tipo: TipoRecomendacion
    payload: dict
    justificacion: str | None = None
    confianza: float | None = None
    aplicada: bool
    aplicada_en: datetime | None = None


class RecomendacionUpdate(BaseModel):
    """Marca una recomendación como aplicada o pendiente."""

    model_config = ConfigDict(extra="forbid")

    aplicada: bool


class CorridaOut(BaseModel):
    """Estado de una corrida para el polling del frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    proyecto_id: uuid.UUID
    estado: str
    modelo: str | None = None
    motor_version: str
    prompt_version: str
    intake_hash: str
    tokens_entrada: int | None = None
    tokens_salida: int | None = None
    duracion_ms: int | None = None
    error_detalle: str | None = None
    iniciado_en: datetime
    terminado_en: datetime | None = None


class CorridaDetalleOut(CorridaOut):
    """Corrida con su entrada y su salida congeladas."""

    entrada: dict
    salida: PropuestaAgente | None = None
    fuentes: list[FuenteOut] = Field(default_factory=list)


class ProductoSolicitado(BaseModel):
    """Un producto que el usuario agregó en el paso 2.

    Llega por código de catálogo o como texto libre; en el segundo caso el backend lo
    investiga antes de armar el intake (ficha curada primero, web como respaldo).
    """

    model_config = ConfigDict(extra="forbid")

    cultivo_codigo: str | None = Field(default=None, min_length=2, max_length=30)
    producto_texto: str | None = Field(default=None, min_length=2, max_length=60)
    prioridad: int | None = Field(default=None, ge=1, le=9)


class CorridaIniciarIn(BaseModel):
    """Cuerpo opcional del disparo del agente."""

    model_config = ConfigDict(extra="forbid")

    productos: list[ProductoSolicitado] = Field(default_factory=list, max_length=8)
    siembra: date | None = None


class CorridaIniciadaOut(BaseModel):
    """Respuesta 202 al disparar el agente: el front empieza a hacer polling."""

    corrida_id: uuid.UUID
    estado: str
    intake_hash: str


class ResultadoProyectoOut(BaseModel):
    """Paso 4: documento de solo lectura que junta todo el proyecto."""

    proyecto_id: uuid.UUID
    nombre: str
    estado: EstadoProyecto
    diseno: DisenoGenerado
    advertencias: list[Advertencia] = Field(default_factory=list)
