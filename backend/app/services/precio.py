"""Precios de materiales investigados por el agente (S6, pasos 4).

El agente busca precios con fuentes web; el backend los guarda una sola vez por
material y las corridas siguientes —de cualquier usuario— los reutilizan mientras
sigan vigentes. El motor sigue siendo el dueño de las cantidades: acá solo se
persisten precios unitarios, moneda, fuente y fecha de recuperación.

Dos operaciones, ambas idempotentes:

* ``reutilizar`` completa con la base los materiales que el agente no cotizó y cuenta
  cuántos reutilizó. Un precio más viejo que la vigencia no se toca: se investiga de
  nuevo.
* ``guardar`` hace upsert de los precios que el agente sí trajo, sin duplicar filas y
  sin guardar precios ausentes o no positivos.

El acceso a la base vive acá porque la tabla es del flujo del agente y no tiene
repositorio propio; el upsert es una sola declaración por material.
"""

from __future__ import annotations

import math
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.material_precio import MaterialPrecio
from app.schemas.agente import MaterialAgente

__all__ = [
    "VIGENCIA_DIAS",
    "clave",
    "completar_totales",
    "guardar",
    "reutilizar",
    "vigentes",
]

# Un precio de más de 90 días se considera vencido para el informe y se vuelve a
# investigar. Es un único número para que la corrida y el contexto no discrepen.
VIGENCIA_DIAS = 90
# Tope de precios que viajan al prompt: el contexto no puede crecer sin límite y solo
# lleva las familias de un sistema de riego.
MAX_PRECIOS_CONTEXTO = 40
CLAVE_MAX = 300

# Unidades equivalentes -> forma canónica. Sin esto el mismo material genera una fila
# vigente por cada forma en que el agente escribe la unidad ("m", "mt", "Metro").
_UNIDADES_METRO = {
    "m",
    "m.",
    "ml",
    "ml.",
    "mt",
    "mts",
    "metro",
    "metros",
    "metro lineal",
    "metros lineales",
}
_UNIDADES_UNIDAD = {
    "u",
    "un",
    "und",
    "unidad",
    "unidades",
    "pza",
    "pzas",
    "pieza",
    "piezas",
}

# Familias del cómputo de riego. El prompt solo recibe precios de estas familias: el
# costo de una malla antigranizo o de semilla no lo calcula este paso.
_FAMILIAS_RIEGO = (
    "tuber",
    "pvc",
    "manguera",
    "goter",
    "emisor",
    "valvul",
    "tanque",
    "bomba",
    "conexion",
    "filtro",
    "riego",
    "hidraul",
)


def _normalizar(texto: str) -> str:
    """Minúsculas, sin acentos y con los espacios colapsados."""

    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(
        caracter for caracter in descompuesto if not unicodedata.combining(caracter)
    )
    return " ".join(sin_tildes.lower().split())


def clave(rubro: str, descripcion: str, unidad: str) -> str:
    """Identidad normalizada del material: la misma en cualquier corrida.

    "Tubería principal", "PVC 32 mm" y "M" tienen que reconocerse igual aunque el
    agente escriba tildes, mayúsculas, espacios internos de más o una unidad
    equivalente ("mt", "Metro").
    """

    return "|".join(
        (_normalizar(rubro), _normalizar(descripcion), _unidad_canonica(unidad))
    )[:CLAVE_MAX]


def _unidad_canonica(unidad: str) -> str:
    texto = _normalizar(unidad)
    if texto in _UNIDADES_METRO:
        return "m"
    if texto in _UNIDADES_UNIDAD:
        return "u"
    return texto


def _es_familia_riego(rubro: str, descripcion: str) -> bool:
    """Si el material pertenece al cómputo de un sistema de riego."""

    texto = _normalizar(f"{rubro} {descripcion}")
    return any(familia in texto for familia in _FAMILIAS_RIEGO)


def clave_material(material: MaterialAgente) -> str:
    return clave(material.rubro, material.descripcion, material.unidad)


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _con_zona(valor: datetime) -> datetime:
    """SQLite devuelve las fechas sin zona: se asumen UTC, que es como se guardan."""

    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _vigente(fila: MaterialPrecio, corte: datetime) -> bool:
    return _con_zona(fila.recuperado_en) >= corte


def _precio_valido(precio: float | None) -> bool:
    return precio is not None and math.isfinite(float(precio)) and float(precio) > 0


def _fecha_agente(valor: datetime | None, ahora: datetime) -> datetime:
    """Fecha de recuperación a guardar: la del agente o el momento del guardado."""

    if valor is None:
        return ahora
    return _con_zona(valor)


def vigentes(
    db: Session,
    vigencia_dias: int = VIGENCIA_DIAS,
    limite: int = MAX_PRECIOS_CONTEXTO,
) -> list[MaterialPrecio]:
    """Precios vigentes de las familias de riego, del más reciente al más viejo.

    El filtro por familia se hace después de la fecha y antes del tope: el contexto
    no gasta lugar en precios que este paso no usa.
    """

    corte = _ahora() - timedelta(days=max(vigencia_dias, 0))
    tope = max(limite, 0)
    if tope == 0:
        return []
    stmt = (
        select(MaterialPrecio)
        .where(MaterialPrecio.recuperado_en >= corte)
        .order_by(
            MaterialPrecio.actualizado_en.desc(),
            MaterialPrecio.recuperado_en.desc(),
            MaterialPrecio.clave,
        )
    )
    precios: list[MaterialPrecio] = []
    for fila in db.scalars(stmt).all():
        if not _vigente(fila, corte):
            continue
        if not _es_familia_riego(fila.rubro, fila.descripcion):
            continue
        precios.append(fila)
        if len(precios) >= tope:
            break
    return precios


def reutilizar(
    db: Session, materiales: list[MaterialAgente], vigencia_dias: int
) -> int:
    """Completa con el precio guardado vigente los materiales que el agente no trajo.

    Devuelve cuántos materiales se reutilizaron. Un material que el agente ya cotizó
    no se toca: su precio, su fuente y su fecha investigados en esta corrida mandan.
    """

    corte = _ahora() - timedelta(days=max(vigencia_dias, 0))
    reutilizados = 0

    for material in materiales:
        if _precio_valido(material.precio_unitario_bs):
            continue

        stmt = (
            select(MaterialPrecio)
            .where(MaterialPrecio.clave == clave_material(material))
            .order_by(
                MaterialPrecio.recuperado_en.desc(),
                MaterialPrecio.actualizado_en.desc(),
                MaterialPrecio.id,
            )
        )
        fila = db.scalars(stmt).first()
        if fila is None or not _vigente(fila, corte):
            continue

        material.precio_unitario_bs = float(fila.precio_unitario_bs)
        material.moneda = fila.moneda
        material.fuente_url = fila.fuente_url
        material.recuperado_en = _con_zona(fila.recuperado_en)
        material.reutilizado = True
        reutilizados += 1

    return reutilizados


def completar_totales(materiales: list[MaterialAgente]) -> int:
    """Completa ``total_bs`` cuando hay cantidad y precio y no lo informó el agente.

    Devuelve cuántos totales se completaron. Sin precio no hay total: nunca se
    rellena con cero un rubro que el agente no cotizó.
    """

    completados = 0
    for material in materiales:
        if material.total_bs is not None:
            continue
        if not _precio_valido(material.precio_unitario_bs):
            continue
        cantidad = material.cantidad
        if cantidad is None or not math.isfinite(float(cantidad)) or cantidad <= 0:
            continue
        material.total_bs = round(float(material.precio_unitario_bs) * cantidad, 2)
        completados += 1
    return completados


def guardar(db: Session, materiales: list[MaterialAgente]) -> int:
    """Upsert de los precios que el agente trajo, uno por material.

    No guarda precios ausentes ni no positivos y no vuelve a escribir los que esta
    corrida reutilizó de la base: eso pisotearía la fecha original del precio.
    Devuelve cuántos precios se guardaron.
    """

    ahora = _ahora()
    guardados = 0

    # Un lote puede traer dos rubros que normalizan a la misma clave ("PVC 32 mm" y
    # "PVC  32  mm"): se colapsan antes de tocar la base. Si ambos tienen precio gana
    # el último; uno sin precio nunca reemplaza a uno con precio.
    pendientes: dict[str, MaterialAgente] = {}
    for material in materiales:
        if material.reutilizado:
            continue
        if not _precio_valido(material.precio_unitario_bs):
            continue
        pendientes[clave_material(material)] = material

    for identidad, material in pendientes.items():
        fila = (
            db.scalars(
                select(MaterialPrecio)
                .where(MaterialPrecio.clave == identidad)
                .order_by(
                    MaterialPrecio.actualizado_en.desc(),
                    MaterialPrecio.recuperado_en.desc(),
                    MaterialPrecio.id,
                )
            ).first()
        )
        recuperado_en = _fecha_agente(material.recuperado_en, ahora)

        if fila is None:
            fila = MaterialPrecio(
                id=uuid.uuid4(),
                clave=identidad,
                rubro=material.rubro[:60],
                descripcion=material.descripcion[:200],
                unidad=_unidad_canonica(material.unidad)[:20],
                moneda=material.moneda,
                precio_unitario_bs=material.precio_unitario_bs,
                fuente_url=material.fuente_url,
                recuperado_en=recuperado_en,
                actualizado_en=ahora,
            )
            db.add(fila)
        else:
            fila.rubro = material.rubro[:60]
            fila.descripcion = material.descripcion[:200]
            fila.unidad = _unidad_canonica(material.unidad)[:20]
            fila.moneda = material.moneda
            fila.precio_unitario_bs = material.precio_unitario_bs
            fila.fuente_url = material.fuente_url
            fila.recuperado_en = recuperado_en
            fila.actualizado_en = ahora
        guardados += 1

    if guardados:
        db.commit()
    return guardados
