"""Contratos de los bloques de cultivo y del balance de área.

Dos modos de reparto mutuamente excluyentes en la entrada: ``porcentaje`` (el motor
reparte el terreno) y ``poligono`` (el bloque ya viene dibujado o editado). En ambos
casos el área la calcula el backend a partir de la geometría.
"""

import uuid
from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import OrigenBloque
from app.schemas.comun import Advertencia, Poligono


class ModoReparto(StrEnum):
    PORCENTAJE = "porcentaje"
    POLIGONO = "poligono"


class EstadoBalance(StrEnum):
    CORRECTO = "correcto"
    AJUSTADO = "ajustado"
    EXCEDIDO = "excedido"


class BloqueCultivoCreate(BaseModel):
    """Alta de un bloque de cultivo en el proyecto."""

    model_config = ConfigDict(extra="forbid")

    # Uno de los dos: el código del catálogo o el producto tal como lo escribió el
    # usuario. Con ``producto_texto`` el backend investiga (ficha curada primero,
    # web como respaldo) y da de alta la ficha si no existía.
    cultivo_codigo: str | None = Field(default=None, min_length=2, max_length=30)
    producto_texto: str | None = Field(default=None, min_length=2, max_length=60)
    etiqueta: str | None = Field(default=None, max_length=60)
    siembra: date | None = None
    cosecha: date | None = None
    demanda_l_m2_dia: float | None = Field(default=None, ge=0, le=20)
    modo: ModoReparto = ModoReparto.PORCENTAJE
    porcentaje: float | None = Field(default=None, gt=0, le=100)
    poligono: Poligono | None = None

    @model_validator(mode="after")
    def _exigir_producto(self) -> "BloqueCultivoCreate":
        if bool(self.cultivo_codigo) == bool(self.producto_texto):
            raise ValueError(
                "Indicá 'cultivo_codigo' o 'producto_texto', nunca los dos ni ninguno."
            )
        return self

    @model_validator(mode="after")
    def _exigir_dato_del_modo(self) -> "BloqueCultivoCreate":
        if self.modo is ModoReparto.PORCENTAJE and self.porcentaje is None:
            raise ValueError("El modo 'porcentaje' requiere el campo 'porcentaje'.")
        if self.modo is ModoReparto.POLIGONO and self.poligono is None:
            raise ValueError("El modo 'poligono' requiere el campo 'poligono'.")
        return self


class BloqueCultivoUpdate(BaseModel):
    """Edición parcial: mover el polígono, cambiar fechas o ajustar la demanda."""

    model_config = ConfigDict(extra="forbid")

    etiqueta: str | None = Field(default=None, max_length=60)
    siembra: date | None = None
    cosecha: date | None = None
    demanda_l_m2_dia: float | None = Field(default=None, ge=0, le=20)
    porcentaje: float | None = Field(default=None, gt=0, le=100)
    poligono: Poligono | None = None


class AptitudSuelo(BaseModel):
    """Veredicto del cultivo sobre el suelo del terreno.

    Es informativo: el suelo nunca bloquea el avance del paso 2, porque un cultivo
    puede crecer fuera de su suelo ideal con otro manejo. ``None`` en el bloque
    significa que no sabemos (ni la ficha ni la investigación traen ese suelo).
    """

    veredicto: Literal["apto", "condicionado", "no_apto"]
    motivo: str | None = None
    fuente: str | None = None


class BloqueCultivoOut(BaseModel):
    """Bloque persistido, con el área derivada y todo lo que muestra el paso 2."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cultivo_codigo: str
    etiqueta: str | None = None
    area_m2: float
    poligono: Poligono
    siembra: date | None = None
    cosecha: date | None = None
    demanda_l_m2_dia: float
    orden: int
    origen: OrigenBloque
    # Derivados por el backend para que el front no calcule nada.
    porcentaje: float = 0.0
    demanda_total_l_dia: float = 0.0
    ciclo_dias: int | None = None
    kc: float | None = None
    dias_a_cosecha: int | None = None
    aptitud_suelo: AptitudSuelo | None = None
    advertencias: list[Advertencia] = Field(default_factory=list)


class CicloCultivo(BaseModel):
    """Intervalo de siembra a cosecha de un bloque."""

    cultivo_codigo: str
    desde: date | None = None
    hasta: date | None = None


class SolapeCiclo(BaseModel):
    """Dos o más bloque con ciclo superpuesto: define la demanda pico."""

    desde: date
    hasta: date
    cultivos: list[str] = Field(default_factory=list)


class BalanceArea(BaseModel):
    """Panel derecho del paso 2: siempre completo, calculado por el backend."""

    terreno_m2: float
    asignado_m2: float
    disponible_m2: float
    estado: EstadoBalance
    demanda_total_l_dia: float
    demanda_prom_l_m2_dia: float
    calendario: list[CicloCultivo] = Field(default_factory=list)
    solapes: list[SolapeCiclo] = Field(default_factory=list)
    alertas: list[Advertencia] = Field(default_factory=list)


class CultivoRespuesta(BaseModel):
    """Respuesta de cualquier escritura del paso 2: el bloque y el balance completo.

    ``advertencias`` trae lo que pasó con la ficha del cultivo: ``CULTIVO_INVESTIGADO``
    (el agente la creó y requiere revisión) o ``PRODUCTO_NO_RECONOCIDO``.
    """

    bloque: BloqueCultivoOut
    balance: BalanceArea
    advertencias: list[Advertencia] = Field(default_factory=list)
