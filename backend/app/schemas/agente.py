"""Contrato del agente de recomendaciones y del diseño que produce el motor.

``PropuestaAgente`` es el ``response_model`` del agente: **no contiene geometría**.
El agente elige cultivos y justifica; el motor determinístico calcula polígonos,
sectores, red y cómputo. Un LLM que devuelve coordenadas devuelve ficción.
"""

import hashlib
import json
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    EstadoProyecto,
    FuenteAgua,
    OrigenCaudal,
    TipoFuenteAgente,
    TipoRecomendacion,
)
from app.schemas.comun import Advertencia, Poligono, Punto
from app.schemas.cultivo import AptitudSuelo
from app.schemas.proyecto import GeometriaTerreno, LadoMedido
from app.schemas.riego import ComputoOut, RedOut, SectorOut, SistemaRiegoOut

# --------------------------------------------------------------------------- #
# Entrada del agente
# --------------------------------------------------------------------------- #


class FichaFuente(BaseModel):
    """Fuente de una ficha agronómica, tal como la modela el catálogo o el curado.

    Es la misma forma que ``agente_fuentes``: el agente puede citarla sin que el
    backend tenga que traducirla.
    """

    model_config = ConfigDict(extra="forbid")

    tipo: str = Field(min_length=2, max_length=30)
    titulo: str | None = Field(default=None, max_length=300)
    url: str | None = Field(default=None, max_length=1000)
    fragmento: str | None = Field(default=None, max_length=1000)


class ProductoDeseado(BaseModel):
    """Un producto que el cliente quiere sembrar, con su ficha completa.

    Los datos agronómicos llegan del catálogo y, si el catálogo no los tiene, de la
    ficha curada. ``None`` significa que el dato no está modelado: el agente no debe
    inventarlo.
    """

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=2, max_length=60)
    # Código de catálogo cuando el producto ya lo tiene; el texto libre queda sin
    # código hasta que la investigación lo da de alta.
    cultivo_codigo: str | None = Field(default=None, min_length=2, max_length=30)
    prioridad: int = Field(default=1, ge=1, le=9)
    area_deseada_m2: float | None = Field(default=None, gt=0)
    kc: float | None = Field(default=None, ge=0, le=2)
    aptitud_suelo: dict[str, AptitudSuelo] | None = None
    profundidad_raiz_cm: int | None = Field(default=None, ge=1, le=300)
    densidad_plantas_m2: float | None = Field(default=None, gt=0, le=500)
    meses_siembra: list[int] | None = None
    fuentes: list[FichaFuente] | None = None


class RestriccionesEntrada(BaseModel):
    """Restricciones del paso 3 que el usuario elige antes de generar el informe.

    Viajan en el body de la corrida y quedan congeladas en ``entrada``. Todas son
    opcionales: si el usuario no eligió nada, el agente no debe asumirlo.
    """

    model_config = ConfigDict(extra="forbid")

    energia: Literal["red-electrica", "solar"] | None = None
    tanque_l: float | None = Field(default=None, gt=0, le=1_000_000)
    presupuesto_bs: float | None = Field(default=None, ge=0, le=100_000_000)


class EntradaAgente(BaseModel):
    """Todo lo que el agente puede mirar para armar el informe del paso 4.

    Obligatorio: productos, área, suelo, fuente de agua, caudal efectivo y zona. El
    caudal llega siempre resuelto por el backend: si el cliente no lo informó, el
    sistema ya le asignó uno y lo marca como ``asumido``. El resto de la ficha del
    suelo y del terreno es opcional: ``None`` significa que la base no lo tiene.
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
    # Ficha del suelo modelada en la base (S5).
    infiltracion_mm_h: float | None = Field(default=None, gt=0, le=1000)
    retencion_agua_mm_m: float | None = Field(default=None, gt=0, le=1000)
    # Geometría y medidas del terreno (S5). ``lados_m`` y ``perimetro_m`` los deriva
    # el backend de los vértices: nunca los manda el cliente.
    lados_m: list[LadoMedido] | None = None
    geometria: GeometriaTerreno | None = None
    perimetro_m: float | None = Field(default=None, gt=0)
    profundidad_nivel_dinamico_m: float | None = Field(default=None, gt=0, le=200)
    restricciones: RestriccionesEntrada | None = None

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
    # Imagen híbrida (S4): primero la ficha curada, después lo que investigue el
    # agente. Las URLs que no sean http(s) las descarta ``validacion``.
    imagen_url: str | None = Field(default=None, max_length=1000)
    imagen_fuente_url: str | None = Field(default=None, max_length=1000)


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
    # Imagen del equipo de cabecera (S4), con la página de donde salió.
    imagen_url: str | None = Field(default=None, max_length=1000)
    imagen_fuente_url: str | None = Field(default=None, max_length=1000)


class TurnoSectorAgente(BaseModel):
    """Turno de riego de un sector, tal como lo informa el agente (S3).

    Los rangos se sanean en ``app.agente.validacion``: acá solo se declara la forma
    para que un valor absurdo del modelo se pueda corregir en vez de romper el
    contrato. ``horas`` es la duración del turno, no la hora de inicio.
    """

    model_config = ConfigDict(extra="forbid")

    sector: int
    horas: float | None = None
    caudal_lh: float | None = None


class CifrasAgente(BaseModel):
    """Balance hidráulico y operativo que el agente decide (S3).

    ``None`` es "no informado": nunca se convierte en cero. La conversión a rangos
    razonables vive en ``validacion.corregir``.
    """

    model_config = ConfigDict(extra="forbid")

    presion_trabajo_bar: float | None = None
    eficiencia_pct: float | None = None
    demanda_pico_l_dia: float | None = None
    autonomia_dias: float | None = None
    tiempo_riego_h: float | None = None
    turnos: list[TurnoSectorAgente] = Field(default_factory=list)


class MaterialAgente(BaseModel):
    """Un rubro del cómputo con su precio y su fuente (S6).

    El motor sigue siendo quien calcula las cantidades; el agente aporta el precio y
    la fuente. Un precio vencido o ausente se reporta, no se inventa.
    """

    model_config = ConfigDict(extra="forbid")

    rubro: str = Field(min_length=1, max_length=60)
    descripcion: str = Field(min_length=1, max_length=200)
    cantidad: float
    unidad: str = Field(min_length=1, max_length=20)
    moneda: str = Field(default="BOB", min_length=3, max_length=3)
    precio_unitario_bs: float | None = None
    total_bs: float | None = None
    fuente_url: str | None = Field(default=None, max_length=1000)


class RecomendacionFinal(BaseModel):
    """Recomendación final del informe, con su justificación (S7)."""

    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1, max_length=120)
    detalle: str = Field(min_length=1, max_length=1000)
    justificacion: str = Field(default="", max_length=600)


class PropuestaAgente(BaseModel):
    """``response_model`` del agente: cultivos + parámetros, nunca geometría.

    El campo ``fuentes`` no lo llena el modelo: lo llena el backend a partir de las
    herramientas de búsqueda que efectivamente se ejecutaron en la corrida. Las
    cifras, los materiales y las recomendaciones son las que el informe del paso 4
    muestra; el motor las usa como objetivo y se ajusta a ellas.
    """

    model_config = ConfigDict(extra="forbid")

    cultivos: list[CultivoRecomendado] = Field(min_length=1, max_length=8)
    sistema: SistemaRecomendado
    cifras: CifrasAgente = Field(default_factory=CifrasAgente)
    materiales: list[MaterialAgente] = Field(default_factory=list)
    recomendaciones: list[RecomendacionFinal] = Field(default_factory=list)
    advertencias: list[Advertencia] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Corridas: fuentes y recomendaciones persistidas
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


# --------------------------------------------------------------------------- #
# Geometría generada por el motor
# --------------------------------------------------------------------------- #


class CifrasMotor(BaseModel):
    """Cifras que calcula el motor determinístico para el informe (S9).

    ``None`` es "no informado": el motor nunca rellena con cero un dato que no
    calculó. El agente propone en ``CifrasAgente`` y ``AjusteMotor`` explica la
    diferencia cuando el motor tuvo que recalcular.

    ``caudal_sector_m3h`` sale de los sectores generados; con más de un sector es el
    del sector de mayor gasto. Sin red generada cae al caudal del preview.
    """

    presion_trabajo_bar: float | None = None
    caudal_sector_m3h: float | None = None
    tiempo_riego_h: float | None = None
    autonomia_dias: float | None = None
    demanda_pico_l_dia: float | None = None


class AjusteMotor(BaseModel):
    """Una diferencia entre lo que propuso el agente y lo que hizo el motor (S3).

    ``valor_agente`` y ``valor_motor`` son texto ya formateado para el informe: así
    un ajuste de área, de presión o de cómputo comparte la misma forma y el front no
    tiene que interpretar unidades.

    El motor solo computa tubería, goteros y válvulas: los rubros del BOM que no
    calcula (tanque, bomba y conexiones) no se contrastan y nunca generan un ajuste.
    """

    campo: str
    valor_agente: str | None = None
    valor_motor: str | None = None
    motivo: str


class CalendarioBloque(BaseModel):
    """Siembra y cosecha de un bloque del cultivo (S9)."""

    bloque_id: uuid.UUID
    cultivo_codigo: str
    etiqueta: str | None = None
    siembra: date | None = None
    cosecha: date | None = None


class RecomendacionInforme(BaseModel):
    """Recomendación final del informe, con su justificación (S7).

    Las filas de ``agente_recomendaciones`` llegan con su ``tipo`` y sus marcas de
    aplicación. Las recomendaciones finales del agente (``RecomendacionFinal``) no
    tienen tipo propio en la base sin una migración: se informan con
    ``tipo="final"`` y ``aplicada=None`` (no informado), nunca con un valor
    inventado.
    """

    id: uuid.UUID | None = None
    tipo: str
    titulo: str
    detalle: str | None = None
    justificacion: str | None = None
    aplicada: bool | None = None


class BloqueGenerado(BaseModel):
    """Bloque de cultivo con su polígono listo para pintar."""

    id: uuid.UUID
    cultivo_codigo: str
    color: str
    poligono: Poligono
    area_m2: float
    centroide: Punto
    nombre: str | None = None
    # Área del bloque sobre el terreno. None si el terreno no informa su área.
    porcentaje: float | None = None
    demanda_pico_l_dia: float | None = None
    siembra: date | None = None
    cosecha: date | None = None
    ciclo_dias: int | None = None
    kc: float | None = None
    imagen_url: str | None = None


class DisenoGenerado(BaseModel):
    """Salida completa del motor: lo que el front pinta y el PDF consume."""

    bloques: list[BloqueGenerado] = Field(default_factory=list)
    sistema: SistemaRiegoOut
    sectores: list[SectorOut] = Field(default_factory=list)
    red: RedOut = Field(default_factory=RedOut)
    computo: ComputoOut
    advertencias: list[Advertencia] = Field(default_factory=list)
    # Cifras del motor y las que propuso el agente, para poder compararlas (S3, S9).
    cifras: CifrasMotor = Field(default_factory=CifrasMotor)
    cifras_agente: CifrasAgente | None = None
    eficiencia_pct: float | None = None
    calendario: list[CalendarioBloque] = Field(default_factory=list)
    materiales: list[MaterialAgente] = Field(default_factory=list)
    recomendaciones: list[RecomendacionInforme] = Field(default_factory=list)
    fuentes: list[FuenteOut] = Field(default_factory=list)
    ajustes: list[AjusteMotor] = Field(default_factory=list)


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
    recomendaciones: list[RecomendacionOut] = Field(default_factory=list)


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
    """Cuerpo opcional del disparo del agente.

    ``restricciones`` llega del paso 3 y se congela en ``entrada`` junto con el resto
    del intake: así T2 puede consumirlas sin volver a pedirlas y la corrida queda
    reproducible.
    """

    model_config = ConfigDict(extra="forbid")

    productos: list[ProductoSolicitado] = Field(default_factory=list, max_length=8)
    siembra: date | None = None
    restricciones: RestriccionesEntrada | None = None


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
