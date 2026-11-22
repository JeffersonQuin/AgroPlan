"""Contratos de proyecto y terreno.

Regla que estos schemas hacen cumplir: el cliente envía **geometría**, nunca áreas
ni perímetros. Las entradas declaran ``extra="forbid"`` para que un ``area_m2``
enviado por error termine en 422 en lugar de desincronizar el cómputo del paso 4.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    EstadoProyecto,
    FormaTerreno,
    FuenteAgua,
    OrigenCaudal,
    UnidadSistema,
)
from app.schemas.comun import Advertencia, RangoCaudal

# --------------------------------------------------------------------------- #
# Proyecto
# --------------------------------------------------------------------------- #


class ProyectoCreate(BaseModel):
    """Alta desde el modal de proyectos: nombre requerido, zona opcional."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=60)
    zona: str | None = Field(default=None, max_length=120)
    unidad: UnidadSistema = UnidadSistema.METRICO


class ProyectoUpdate(BaseModel):
    """Autosave de la cabecera. ``version`` es la del cliente: si no coincide, 409."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    zona: str | None = Field(default=None, max_length=120)
    unidad: UnidadSistema | None = None
    paso_actual: int | None = Field(default=None, ge=1, le=4)
    ultimo_paso_completado: int | None = Field(default=None, ge=0, le=4)
    version: int = Field(ge=1)


class ProyectoOut(BaseModel):
    """Proyecto completo, tal como lo reabre el wizard."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    zona: str | None = None
    unidad: UnidadSistema
    estado: EstadoProyecto
    paso_actual: int
    ultimo_paso_completado: int
    version: int
    corrida_actual_id: uuid.UUID | None = None
    creado_en: datetime
    actualizado_en: datetime


class ProyectoListadoOut(BaseModel):
    """Ítem de la grilla de proyectos: solo lo que dibuja la tarjeta.

    Los derivados (``area_m2``, ``cultivos_count``, ``sistema_tipo``) los calcula el
    backend; las etiquetas visuales las arma el frontend.
    """

    id: uuid.UUID
    nombre: str
    zona: str | None = None
    unidad: UnidadSistema
    estado: EstadoProyecto
    area_m2: float | None = None
    cultivos_count: int = 0
    sistema_tipo: str | None = None
    ultimo_paso_completado: int
    actualizado_en: datetime
    version: int


# --------------------------------------------------------------------------- #
# Terreno
# --------------------------------------------------------------------------- #


class Vertice(BaseModel):
    """Vértice del contorno, en metros, con origen en el mínimo del bounding box."""

    model_config = ConfigDict(extra="forbid")

    x: float
    y: float


class TerrenoIn(BaseModel):
    """Entrada del paso 1.

    ``caudal_disponible_m3h`` es opcional: si falta o llega ``null``, el sistema asigna
    el caudal de referencia de la fuente de agua y lo registra como ``asumido``. Si
    llega un valor, queda como ``cliente`` y ese es el que usa todo el sistema.
    """

    model_config = ConfigDict(extra="forbid")

    nombre_parcela: str = Field(min_length=1, max_length=60)
    forma: FormaTerreno = FormaTerreno.RECTANGULO
    vertices: list[Vertice] = Field(min_length=3, max_length=30)
    suelo_codigo: str = Field(min_length=2, max_length=20)
    pendiente_pct: float = Field(default=0, ge=0, le=30)
    fuente_agua: FuenteAgua
    # Paso 1 del prototipo: profundidad del nivel dinámico del pozo.
    profundidad_nivel_dinamico_m: float | None = Field(default=None, gt=0, le=200)
    caudal_disponible_m3h: float | None = Field(default=None, gt=0, le=50)


class TerrenoUpdate(BaseModel):
    """Edición parcial del paso 1, incluido el caudal que el sistema había asumido.

    El caudal es tri-estado: campo ausente = no se toca; ``null`` explícito = se borra el
    valor del cliente y el sistema vuelve a asignarlo desde la fuente de agua
    (procedencia ``asumido``); un número = procedencia ``cliente``. Por eso un consumidor
    debe mirar ``model_fields_set`` para distinguir "ausente" de "null".
    """

    model_config = ConfigDict(extra="forbid")

    nombre_parcela: str | None = Field(default=None, min_length=1, max_length=60)
    # La forma es una etiqueta del terreno; el guardado completo la manda siempre, así
    # que el PATCH tiene que aceptarla o el payload entero se rechaza.
    forma: FormaTerreno | None = None
    vertices: list[Vertice] | None = None
    suelo_codigo: str | None = Field(default=None, min_length=2, max_length=20)
    pendiente_pct: float | None = Field(default=None, ge=0, le=30)
    fuente_agua: FuenteAgua | None = None
    profundidad_nivel_dinamico_m: float | None = Field(default=None, gt=0, le=200)
    caudal_disponible_m3h: float | None = Field(default=None, gt=0, le=50)

    @property
    def limpia_caudal(self) -> bool:
        """True si el cliente pidió volver al caudal asumido por el sistema."""

        return (
            "caudal_disponible_m3h" in self.model_fields_set
            and self.caudal_disponible_m3h is None
        )


class GeometriaTerreno(BaseModel):
    """Forma persistida del terreno."""

    vertices: list[Vertice]
    cerrado: bool = True
    unidad: str = "m"
    eje_y: str = "norte"


class LadoMedido(BaseModel):
    """Cota de un lado del polígono, derivada de los vértices."""

    desde: int
    hasta: int
    longitud_m: float


class TerrenoOut(BaseModel):
    """Terreno con sus derivados y el caudal ya resuelto."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre_parcela: str
    forma: FormaTerreno
    geometria: GeometriaTerreno
    area_m2: float
    perimetro_m: float
    lados: int
    lados_m: list[LadoMedido] = Field(default_factory=list)
    suelo_codigo: str
    pendiente_pct: float
    fuente_agua: FuenteAgua
    caudal_disponible_m3h: float | None = None
    caudal_efectivo_m3h: float
    caudal_origen: OrigenCaudal
    profundidad_nivel_dinamico_m: float | None = None
    # Se completan en el servicio, no viven en la tabla.
    caudal_sugerido_m3h: float | None = None
    caudal_rango_sugerido_m3h: RangoCaudal | None = None
    alertas: list[Advertencia] = Field(default_factory=list)
