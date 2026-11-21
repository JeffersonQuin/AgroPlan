"""Contratos de los bloques de cultivo y del balance de área.

Dos modos de reparto mutuamente excluyentes en la entrada: ``porcentaje`` (el motor
reparte el terreno) y ``poligono`` (el bloque ya viene dibujado o editado). En ambos
casos el área la calcula el backend a partir de la geometría.
"""

import uuid
from datetime import date
from enum import StrEnum

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

    cultivo_codigo: str = Field(min_length=2, max_length=30)
    etiqueta: str | None = Field(default=None, max_length=60)
    siembra: date | None = None
    cosecha: date | None = None
    demanda_l_m2_dia: float | None = Field(default=None, ge=0, le=20)
    modo: ModoReparto = ModoReparto.PORCENTAJE
    porcentaje: float | None = Field(default=None, gt=0, le=100)
    poligono: Poligono | None = None

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


class BloqueCultivoOut(BaseModel):
    """Bloque persistido, con el área ya derivada."""

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
    """Respuesta de cualquier escritura del paso 2: el bloque y el balance completo."""

    bloque: BloqueCultivoOut
    balance: BalanceArea
