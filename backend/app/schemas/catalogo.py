"""Contratos de los catálogos: solo lectura para la API."""

from pydantic import BaseModel, ConfigDict

from app.models.catalogo import Cultivo, Suelo  # noqa: F401  (referencia de origen)


class CultivoOut(BaseModel):
    """Ficha de un cultivo del catálogo mínimo."""

    model_config = ConfigDict(from_attributes=True)

    codigo: str
    nombre: str
    icono: str
    color: str
    demanda_agua_l_m2_dia: float
    demanda_agua_l_planta_dia: float | None = None
    ciclo_dias: int
    densidad_plantas_m2: float | None = None
    profundidad_raiz_cm: int | None = None
    meses_siembra: list[int] | None = None
    activo: bool = True


class SueloOut(BaseModel):
    """Tipo de suelo con su capacidad de infiltración."""

    model_config = ConfigDict(from_attributes=True)

    codigo: str
    nombre: str
    infiltracion_mm_h: float
    retencion_agua_mm_m: float | None = None
