"""Contratos de los catálogos: solo lectura para la API."""

from datetime import datetime

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
    kc: float | None = None
    aptitud_suelo: dict | None = None
    activo: bool = True
    # ``agente``: la ficha la creó el agente al investigar un producto nuevo y queda
    # pendiente de revisión, con las fuentes que usó.
    origen: str = "humano"
    revisado_en: datetime | None = None
    fuentes: list[dict] | None = None


class SueloOut(BaseModel):
    """Tipo de suelo con su capacidad de infiltración."""

    model_config = ConfigDict(from_attributes=True)

    codigo: str
    nombre: str
    infiltracion_mm_h: float
    retencion_agua_mm_m: float | None = None
