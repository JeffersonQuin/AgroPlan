"""Tipos compartidos por varios contratos.

``Advertencia`` es el vocabulario común de validaciones: el backend nunca devuelve
un texto suelto como error de negocio, devuelve un código estable más el mensaje que
ya está en español y listo para mostrar.
"""

from pydantic import BaseModel, ConfigDict, Field


class Advertencia(BaseModel):
    """Resultado de una validación no estructural.

    ``bloqueante`` corta el avance del paso; el resto se muestra como aviso. Un dato
    que el sistema asumió (como el caudal) nunca es bloqueante: el usuario no puede
    quedar encerrado por un número que puso el sistema.
    """

    codigo: str = Field(max_length=40)
    mensaje: str = Field(max_length=300)
    bloqueante: bool = False
    campo: str | None = Field(default=None, max_length=40)


class RangoCaudal(BaseModel):
    """Rango de caudal razonable para una fuente de agua, en m³/h."""

    model_config = ConfigDict(extra="forbid")

    min: float
    max: float


class Punto(BaseModel):
    """Punto en metros sobre el sistema de coordenadas del terreno."""

    model_config = ConfigDict(extra="forbid")

    x: float
    y: float


class Poligono(BaseModel):
    """Anillo cerrado de un bloque o sector, en metros."""

    model_config = ConfigDict(extra="forbid")

    anillo: list[tuple[float, float]] = Field(min_length=3)
