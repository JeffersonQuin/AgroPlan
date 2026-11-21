"""Reglas del terreno: geometría derivada y caudal efectivo con procedencia.

El cliente manda vértices, nunca áreas. El caudal es tri-estado: ausente no se toca,
``null`` vuelve al valor asumido por la fuente y un número queda como valor del
cliente.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import FuenteAgua, OrigenCaudal
from app.models.proyecto import Proyecto, Terreno
from app.repository import suelo as suelo_repo
from app.repository import terreno as terreno_repo
from app.schemas.comun import Advertencia, RangoCaudal
from app.schemas.proyecto import LadoMedido, TerrenoIn, TerrenoOut, TerrenoUpdate
from app.services import geometria
from app.services import riego as riego_service

# Caudal de referencia por fuente de agua, en m³/h. Son valores de arranque del
# producto: el usuario siempre puede informar uno propio y queda como "cliente".
CAUDAL_BASE_FUENTE: dict[str, float] = {
    FuenteAgua.PILA.value: 1.5,
    FuenteAgua.POZO.value: 3.0,
    FuenteAgua.RED.value: 5.0,
    FuenteAgua.CISTERNA.value: 2.0,
    FuenteAgua.TANQUE.value: 2.5,
}

FACTOR_RANGO_MIN = 0.6
FACTOR_RANGO_MAX = 1.6


class TerrenoServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _dec(valor: float, lugares: int = 2) -> Decimal:
    return Decimal(str(round(valor, lugares)))


def caudal_sugerido(fuente: str) -> float:
    return CAUDAL_BASE_FUENTE.get(fuente, CAUDAL_BASE_FUENTE[FuenteAgua.PILA.value])


def rango_caudal(fuente: str) -> RangoCaudal:
    base = caudal_sugerido(fuente)
    return RangoCaudal(
        min=round(base * FACTOR_RANGO_MIN, 2),
        max=round(base * FACTOR_RANGO_MAX, 2),
    )


def _derivar_geometria(
    vertices, forma: str
) -> tuple[dict, float, float, int]:
    try:
        puntos = geometria.normalizar_vertices(vertices)
    except (KeyError, TypeError, ValueError) as exc:
        raise TerrenoServiceError(422, "La geometría del terreno no es válida") from exc

    area = geometria.area_poligono(puntos)
    perimetro = geometria.perimetro_poligono(puntos)
    if area <= 0 or perimetro <= 0:
        raise TerrenoServiceError(422, "El terreno debe tener una superficie positiva")

    almacenada = {
        "vertices": [geometria.punto_dict(punto) for punto in puntos],
        "cerrado": True,
        "unidad": "m",
        "eje_y": "norte",
    }
    return almacenada, area, perimetro, len(puntos)


def _validar_suelo(db: Session, codigo: str) -> None:
    if suelo_repo.get_by_codigo(db, codigo) is None:
        raise TerrenoServiceError(422, f"El suelo '{codigo}' no existe en el catálogo")


def _resolver_caudal_cliente(
    caudal: float | None, fuente: str
) -> tuple[Decimal | None, Decimal, str, str | None]:
    """Devuelve (disponible, efectivo, origen, base_fuente) coherentes."""

    if caudal is not None:
        return _dec(caudal, 2), _dec(caudal, 2), OrigenCaudal.CLIENTE.value, None
    base = caudal_sugerido(fuente)
    return None, _dec(base, 2), OrigenCaudal.ASUMIDO.value, fuente


def crear_terreno(db: Session, proyecto: Proyecto, data: TerrenoIn) -> TerrenoOut:
    existente = terreno_repo.get_by_proyecto(db, proyecto.id)
    if existente is not None:
        raise TerrenoServiceError(409, "El proyecto ya tiene terreno; usa PATCH")

    _validar_suelo(db, data.suelo_codigo)
    nombre_parcela = data.nombre_parcela.strip()
    if not nombre_parcela:
        raise TerrenoServiceError(422, "El nombre de la parcela no puede estar vacío")

    geometria_guardada, area, perimetro, lados = _derivar_geometria(
        data.vertices, data.forma.value
    )
    disponible, efectivo, origen, base_fuente = _resolver_caudal_cliente(
        data.caudal_disponible_m3h, data.fuente_agua.value
    )

    terreno = Terreno(
        proyecto_id=proyecto.id,
        nombre_parcela=nombre_parcela,
        forma=data.forma.value,
        geometria=geometria_guardada,
        area_m2=_dec(area),
        perimetro_m=_dec(perimetro),
        lados=lados,
        suelo_codigo=data.suelo_codigo,
        pendiente_pct=_dec(data.pendiente_pct, 2),
        fuente_agua=data.fuente_agua.value,
        caudal_disponible_m3h=disponible,
        caudal_efectivo_m3h=efectivo,
        caudal_origen=origen,
        caudal_base_fuente=base_fuente,
    )
    terreno = terreno_repo.create(db, terreno)
    riego_service.invalidar_diseno(db, proyecto.id)
    return terreno_out(terreno)


def obtener_terreno(db: Session, proyecto: Proyecto) -> TerrenoOut:
    terreno = terreno_repo.get_by_proyecto(db, proyecto.id)
    if terreno is None:
        raise TerrenoServiceError(404, "El proyecto todavía no tiene terreno")
    return terreno_out(terreno)


def actualizar_terreno(
    db: Session, proyecto: Proyecto, data: TerrenoUpdate
) -> TerrenoOut:
    terreno = terreno_repo.get_by_proyecto(db, proyecto.id)
    if terreno is None:
        raise TerrenoServiceError(404, "El proyecto todavía no tiene terreno")

    campos = data.model_fields_set

    if "suelo_codigo" in campos and data.suelo_codigo is not None:
        _validar_suelo(db, data.suelo_codigo)
        terreno.suelo_codigo = data.suelo_codigo

    if "nombre_parcela" in campos and data.nombre_parcela is not None:
        nombre_parcela = data.nombre_parcela.strip()
        if not nombre_parcela:
            raise TerrenoServiceError(
                422, "El nombre de la parcela no puede estar vacío"
            )
        terreno.nombre_parcela = nombre_parcela

    if "vertices" in campos and data.vertices is not None:
        guardada, area, perimetro, lados = _derivar_geometria(
            data.vertices, terreno.forma
        )
        terreno.geometria = guardada
        terreno.area_m2 = _dec(area)
        terreno.perimetro_m = _dec(perimetro)
        terreno.lados = lados

    if "pendiente_pct" in campos and data.pendiente_pct is not None:
        terreno.pendiente_pct = _dec(data.pendiente_pct, 2)

    caudal_cambio = False
    if "fuente_agua" in campos and data.fuente_agua is not None:
        terreno.fuente_agua = data.fuente_agua.value
        caudal_cambio = True

    if data.limpia_caudal:
        base = caudal_sugerido(terreno.fuente_agua)
        terreno.caudal_disponible_m3h = None
        terreno.caudal_efectivo_m3h = _dec(base)
        terreno.caudal_origen = OrigenCaudal.ASUMIDO.value
        terreno.caudal_base_fuente = terreno.fuente_agua
        caudal_cambio = True
    elif "caudal_disponible_m3h" in campos and data.caudal_disponible_m3h is not None:
        terreno.caudal_disponible_m3h = _dec(data.caudal_disponible_m3h)
        terreno.caudal_efectivo_m3h = _dec(data.caudal_disponible_m3h)
        terreno.caudal_origen = OrigenCaudal.CLIENTE.value
        terreno.caudal_base_fuente = None
        caudal_cambio = True
    elif caudal_cambio and terreno.caudal_origen == OrigenCaudal.ASUMIDO.value:
        # Cambió la fuente y el caudal era asumido: se recalcula desde la nueva fuente.
        base = caudal_sugerido(terreno.fuente_agua)
        terreno.caudal_efectivo_m3h = _dec(base)
        terreno.caudal_base_fuente = terreno.fuente_agua

    if caudal_cambio:
        terreno.caudal_actualizado_en = datetime.now(timezone.utc)

    terreno = terreno_repo.update(db, terreno)
    riego_service.invalidar_diseno(db, proyecto.id)
    return terreno_out(terreno)


def terreno_out(terreno: Terreno) -> TerrenoOut:
    salida = TerrenoOut.model_validate(terreno)

    try:
        puntos = geometria.normalizar_vertices(terreno.geometria.get("vertices", []))
        lados_m = [
            LadoMedido(
                desde=indice + 1,
                hasta=(indice + 1) % len(puntos) + 1,
                longitud_m=round(
                    geometria.distancia(puntos[indice], puntos[(indice + 1) % len(puntos)]),
                    2,
                ),
            )
            for indice in range(len(puntos))
        ]
    except (KeyError, TypeError, ValueError):
        lados_m = []

    rango = rango_caudal(terreno.fuente_agua)
    alertas: list[Advertencia] = []
    if (
        terreno.caudal_origen == OrigenCaudal.CLIENTE.value
        and not (rango.min <= float(terreno.caudal_efectivo_m3h) <= rango.max)
    ):
        alertas.append(
            Advertencia(
                codigo="caudal_fuera_de_rango",
                mensaje=(
                    "El caudal informado está fuera del rango habitual para esta "
                    "fuente de agua. El sistema lo respeta, pero verifica la medición."
                ),
                campo="caudal_disponible_m3h",
            )
        )

    return salida.model_copy(
        update={
            "lados_m": lados_m,
            "caudal_sugerido_m3h": caudal_sugerido(terreno.fuente_agua),
            "caudal_rango_sugerido_m3h": rango,
            "alertas": alertas,
        }
    )
