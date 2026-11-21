"""Bloques de cultivo: área derivada, reparto y balance del paso 2.

El cliente puede pedir un reparto por porcentaje (el motor dibuja el bloque) o
enviar un polígono ya editado. En ambos casos el área sale de la geometría, nunca
del payload.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.catalogo import Cultivo
from app.models.enums import OrigenCultivo
from app.models.proyecto import Proyecto, Terreno
from app.models.proyecto_cultivo import ProyectoCultivo
from app.repository import cultivo as cultivo_repo
from app.repository import proyecto_cultivo as bloque_repo
from app.repository import sector_bloque as sector_bloque_repo
from app.repository import terreno as terreno_repo
from app.schemas.comun import Advertencia
from app.schemas.cultivo import (
    BalanceArea,
    BloqueCultivoCreate,
    BloqueCultivoOut,
    BloqueCultivoUpdate,
    CicloCultivo,
    CultivoRespuesta,
    EstadoBalance,
    ModoReparto,
    SolapeCiclo,
)
from app.services import geometria
from app.services import riego as riego_service


class CultivoServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _dec(valor: float, lugares: int = 2) -> Decimal:
    return Decimal(str(round(valor, lugares)))


def _validar_fechas(siembra: date | None, cosecha: date | None) -> None:
    if siembra is not None and cosecha is not None and cosecha <= siembra:
        raise CultivoServiceError(
            422, "La cosecha debe ser posterior a la siembra"
        )


def _poligono_porcentaje(
    terreno: Terreno,
    porcentaje: float,
    existentes: list[ProyectoCultivo],
    excluir_id: uuid.UUID | None = None,
) -> tuple[dict, float]:
    """Dibuja una franja horizontal cuya área es ``porcentaje`` del terreno."""

    try:
        puntos = geometria.normalizar_vertices(terreno.geometria.get("vertices", []))
    except (KeyError, TypeError, ValueError) as exc:
        raise CultivoServiceError(422, "El terreno no tiene geometría válida") from exc

    x_min, y_min, x_max, y_max = geometria.caja(puntos)
    ancho = x_max - x_min
    alto = y_max - y_min
    area_terreno = float(terreno.area_m2)
    if ancho <= 0 or alto <= 0 or area_terreno <= 0:
        raise CultivoServiceError(422, "El terreno no tiene una superficie utilizable")

    area_objetivo = area_terreno * porcentaje / 100.0
    area_ocupada = sum(
        float(bloque.area_m2)
        for bloque in existentes
        if excluir_id is None or bloque.id != excluir_id
    )

    y_inicio = y_min + (area_ocupada / area_terreno) * alto
    if y_inicio >= y_max - 1e-6:
        raise CultivoServiceError(
            422, "No queda superficie libre para asignar otro bloque"
        )

    alto_bloque = min(area_objetivo / ancho, y_max - y_inicio)
    if alto_bloque <= 1e-6:
        raise CultivoServiceError(
            422, "El porcentaje solicitado no cabe en la superficie disponible"
        )

    franja = geometria.rectangulo(x_min, y_inicio, x_max, y_inicio + alto_bloque)
    return geometria.poligono_dict(franja), geometria.area_poligono(franja)


def _poligono_desde_entrada(poligono) -> tuple[dict, float]:
    try:
        puntos = geometria.normalizar_vertices(poligono.anillo)
    except (KeyError, TypeError, ValueError) as exc:
        raise CultivoServiceError(422, "El polígono del bloque no es válido") from exc

    area = geometria.area_poligono(puntos)
    if area <= 0:
        raise CultivoServiceError(422, "El polígono del bloque no tiene superficie")
    return geometria.poligono_dict(puntos), area


def _terreno_requerido(db: Session, proyecto: Proyecto) -> Terreno:
    terreno = terreno_repo.get_by_proyecto(db, proyecto.id)
    if terreno is None:
        raise CultivoServiceError(
            422, "Primero define el terreno antes de asignar cultivos"
        )
    return terreno


def listar_bloques(db: Session, proyecto: Proyecto) -> list[BloqueCultivoOut]:
    bloques = bloque_repo.list_by_proyecto(db, proyecto.id)
    return [BloqueCultivoOut.model_validate(bloque) for bloque in bloques]


def obtener_bloque(
    db: Session, proyecto: Proyecto, bloque_id: uuid.UUID
) -> BloqueCultivoOut:
    bloque = bloque_repo.get_by_id(db, bloque_id, proyecto.id)
    if bloque is None:
        raise CultivoServiceError(404, "Bloque de cultivo no encontrado")
    return BloqueCultivoOut.model_validate(bloque)


def _resolver_producto(
    db: Session, texto: str
) -> tuple[Cultivo | None, list[Advertencia]]:
    """Resuelve un producto escrito por el usuario que no está en el catálogo.

    Camino híbrido: ficha curada del repo primero; búsqueda web sólo como respaldo y
    con presupuesto. Si el agente tiene que crear la ficha, se guarda con
    ``origen='agente'``, sin revisar y con sus fuentes, y la respuesta lo advierte.
    Nunca inventa: si no hay con qué verificar, no hay cultivo.
    """

    from app.agente.investigacion import (
        InvestigacionError,
        ProductoNoReconocido,
        investigar,
    )

    catalogo = cultivo_repo.list_all(db, solo_activos=True)
    filas = [{"codigo": cultivo.codigo, "nombre": cultivo.nombre} for cultivo in catalogo]

    try:
        investigacion = investigar(texto, catalogo=filas)
    except ProductoNoReconocido:
        return None, [
            Advertencia(
                codigo="PRODUCTO_NO_RECONOCIDO",
                mensaje=(
                    f"No se pudo verificar '{texto}': no hay ficha curada y la búsqueda "
                    "web no está disponible. Cargá la ficha o configurá el agente."
                )[:300],
                bloqueante=True,
                campo="producto_texto",
            )
        ]
    except InvestigacionError as exc:
        return None, [
            Advertencia(
                codigo="INVESTIGACION_FALLIDA",
                mensaje=f"La búsqueda de '{texto}' falló: {exc}"[:300],
                bloqueante=True,
                campo="producto_texto",
            )
        ]

    existente = cultivo_repo.get_by_codigo(db, investigacion.codigo)
    if existente is not None:
        return existente, []

    # Una ficha curada del repo ya la verificó una persona: entra revisada. Lo que
    # viene de la web se usa en el acto pero queda pendiente y con aviso bloqueante.
    desde_web = investigacion.origen == "web"
    ahora = datetime.now(timezone.utc)

    cultivo = Cultivo(
        codigo=investigacion.codigo,
        nombre=investigacion.nombre,
        icono=investigacion.icono,
        color=investigacion.color,
        demanda_agua_l_m2_dia=_dec(investigacion.demanda_agua_l_m2_dia, 3),
        ciclo_dias=investigacion.ciclo_dias,
        meses_siembra=investigacion.meses_siembra,
        activo=True,
        origen=OrigenCultivo.AGENTE.value if desde_web else OrigenCultivo.HUMANO.value,
        revisado_en=None if desde_web else ahora,
        fuentes=[
            {
                "tipo": fuente.tipo,
                "titulo": fuente.titulo,
                "url": fuente.url,
                "fragmento": fuente.fragmento,
            }
            for fuente in investigacion.fuentes
        ],
    )
    db.add(cultivo)
    db.commit()
    db.refresh(cultivo)

    if desde_web:
        return cultivo, [
            Advertencia(
                codigo="CULTIVO_INVESTIGADO",
                mensaje=(
                    f"'{cultivo.nombre}' no estaba en el catálogo: el agente creó la ficha "
                    f"con {len(investigacion.fuentes)} fuente(s) de web y queda pendiente "
                    "de revisión."
                )[:300],
                bloqueante=True,
                campo="cultivo_codigo",
            )
        ]

    return cultivo, [
        Advertencia(
            codigo="CULTIVO_DESDE_FICHA",
            mensaje=(
                f"'{cultivo.nombre}' se dio de alta con la ficha curada de AgroPlan "
                f"({investigacion.busquedas} búsqueda(s) web)."
            )[:300],
            campo="cultivo_codigo",
        )
    ]


def crear_bloque(
    db: Session, proyecto: Proyecto, data: BloqueCultivoCreate
) -> CultivoRespuesta:
    terreno = _terreno_requerido(db, proyecto)

    advertencias: list[Advertencia] = []
    if data.producto_texto is not None:
        cultivo_catalogo, advertencias = _resolver_producto(db, data.producto_texto)
        if cultivo_catalogo is not None and not cultivo_catalogo.activo:
            cultivo_catalogo = None
    else:
        cultivo_catalogo = cultivo_repo.get_by_codigo(db, data.cultivo_codigo or "")
        if cultivo_catalogo is not None and not cultivo_catalogo.activo:
            cultivo_catalogo = None

    if cultivo_catalogo is None:
        if advertencias:
            # El producto no se pudo verificar: el motivo real es más útil que decir
            # que "no existe".
            raise CultivoServiceError(422, advertencias[0].mensaje)
        raise CultivoServiceError(
            422,
            f"El cultivo '{data.cultivo_codigo}' no existe o está inactivo",
        )

    _validar_fechas(data.siembra, data.cosecha)

    if data.modo is ModoReparto.PORCENTAJE:
        if data.porcentaje is None:
            raise CultivoServiceError(422, "El reparto por porcentaje requiere 'porcentaje'")
        existentes = bloque_repo.list_by_proyecto(db, proyecto.id)
        poligono, area = _poligono_porcentaje(
            terreno, data.porcentaje, existentes
        )
    else:
        if data.poligono is None:
            raise CultivoServiceError(422, "El modo polígono requiere 'poligono'")
        poligono, area = _poligono_desde_entrada(data.poligono)

    demanda = (
        float(data.demanda_l_m2_dia)
        if data.demanda_l_m2_dia is not None
        else float(cultivo_catalogo.demanda_agua_l_m2_dia)
    )

    bloque = ProyectoCultivo(
        proyecto_id=proyecto.id,
        cultivo_codigo=cultivo_catalogo.codigo,
        etiqueta=data.etiqueta,
        area_m2=_dec(area),
        poligono=poligono,
        siembra=data.siembra,
        cosecha=data.cosecha,
        demanda_l_m2_dia=_dec(demanda, 3),
        orden=bloque_repo.next_orden(db, proyecto.id),
    )
    bloque = bloque_repo.create(db, bloque)
    riego_service.invalidar_diseno(db, proyecto.id)

    return CultivoRespuesta(
        bloque=BloqueCultivoOut.model_validate(bloque),
        balance=balance(db, proyecto, terreno),
        advertencias=advertencias,
    )


def actualizar_bloque(
    db: Session,
    proyecto: Proyecto,
    bloque_id: uuid.UUID,
    data: BloqueCultivoUpdate,
) -> CultivoRespuesta:
    bloque = bloque_repo.get_by_id(db, bloque_id, proyecto.id)
    if bloque is None:
        raise CultivoServiceError(404, "Bloque de cultivo no encontrado")

    terreno = _terreno_requerido(db, proyecto)
    campos = data.model_fields_set

    if "poligono" in campos and data.poligono is not None and "porcentaje" in campos:
        raise CultivoServiceError(
            422, "Elige un solo modo de reparto: 'porcentaje' o 'poligono'"
        )

    if "porcentaje" in campos and data.porcentaje is not None:
        existentes = bloque_repo.list_by_proyecto(db, proyecto.id)
        poligono, area = _poligono_porcentaje(
            terreno, data.porcentaje, existentes, excluir_id=bloque.id
        )
        bloque.poligono = poligono
        bloque.area_m2 = _dec(area)
    elif "poligono" in campos and data.poligono is not None:
        poligono, area = _poligono_desde_entrada(data.poligono)
        bloque.poligono = poligono
        bloque.area_m2 = _dec(area)

    if "etiqueta" in campos:
        bloque.etiqueta = data.etiqueta
    if "demanda_l_m2_dia" in campos and data.demanda_l_m2_dia is not None:
        bloque.demanda_l_m2_dia = _dec(data.demanda_l_m2_dia, 3)

    siembra = data.siembra if "siembra" in campos else bloque.siembra
    cosecha = data.cosecha if "cosecha" in campos else bloque.cosecha
    _validar_fechas(siembra, cosecha)
    if "siembra" in campos:
        bloque.siembra = data.siembra
    if "cosecha" in campos:
        bloque.cosecha = data.cosecha

    bloque = bloque_repo.update(db, bloque)
    riego_service.invalidar_diseno(db, proyecto.id)

    return CultivoRespuesta(bloque=BloqueCultivoOut.model_validate(bloque), balance=balance(db, proyecto, terreno))


def eliminar_bloque(db: Session, proyecto: Proyecto, bloque_id: uuid.UUID) -> None:
    bloque = bloque_repo.get_by_id(db, bloque_id, proyecto.id)
    if bloque is None:
        raise CultivoServiceError(404, "Bloque de cultivo no encontrado")
    # Sin FK físicas activas en SQLite, se limpian los vínculos a mano.
    sector_bloque_repo.delete_by_proyecto_cultivo(db, bloque.id)
    bloque_repo.delete(db, bloque)
    riego_service.invalidar_diseno(db, proyecto.id)


def balance(
    db: Session, proyecto: Proyecto, terreno: Terreno | None = None
) -> BalanceArea:
    if terreno is None:
        terreno = _terreno_requerido(db, proyecto)

    bloques = bloque_repo.list_by_proyecto(db, proyecto.id)
    terreno_m2 = float(terreno.area_m2)
    asignado_m2 = sum(float(bloque.area_m2) for bloque in bloques)
    disponible_m2 = terreno_m2 - asignado_m2

    tolerancia = max(0.5, terreno_m2 * 0.01)
    if asignado_m2 > terreno_m2 + 0.01:
        estado = EstadoBalance.EXCEDIDO
    elif abs(disponible_m2) <= tolerancia:
        estado = EstadoBalance.CORRECTO
    else:
        estado = EstadoBalance.AJUSTADO

    demanda_total = sum(
        float(bloque.area_m2) * float(bloque.demanda_l_m2_dia) for bloque in bloques
    )
    demanda_prom = demanda_total / terreno_m2 if terreno_m2 > 0 else 0.0

    calendario = [
        CicloCultivo(
            cultivo_codigo=bloque.cultivo_codigo,
            desde=bloque.siembra,
            hasta=bloque.cosecha,
        )
        for bloque in bloques
        if bloque.siembra is not None or bloque.cosecha is not None
    ]

    solapes: list[SolapeCiclo] = []
    con_fechas = [
        bloque
        for bloque in bloques
        if bloque.siembra is not None and bloque.cosecha is not None
    ]
    for indice, primero in enumerate(con_fechas):
        for segundo in con_fechas[indice + 1 :]:
            desde = max(primero.siembra, segundo.siembra)
            hasta = min(primero.cosecha, segundo.cosecha)
            if desde < hasta:
                solapes.append(
                    SolapeCiclo(
                        desde=desde,
                        hasta=hasta,
                        cultivos=[primero.cultivo_codigo, segundo.cultivo_codigo],
                    )
                )

    alertas: list[Advertencia] = []
    if estado is EstadoBalance.EXCEDIDO:
        alertas.append(
            Advertencia(
                codigo="area_excedida",
                mensaje=(
                    f"La superficie asignada ({asignado_m2:.2f} m²) supera el terreno "
                    f"({terreno_m2:.2f} m²). Ajusta los bloques para continuar."
                ),
                bloqueante=True,
                campo="area_m2",
            )
        )
    elif estado is EstadoBalance.AJUSTADO:
        alertas.append(
            Advertencia(
                codigo="area_sin_asignar",
                mensaje=(
                    f"Quedan {max(disponible_m2, 0):.2f} m² sin asignar. Puedes "
                    "continuar o repartir el resto entre los cultivos."
                ),
                campo="area_m2",
            )
        )

    return BalanceArea(
        terreno_m2=round(terreno_m2, 2),
        asignado_m2=round(asignado_m2, 2),
        disponible_m2=round(disponible_m2, 2),
        estado=estado,
        demanda_total_l_dia=round(demanda_total, 2),
        demanda_prom_l_m2_dia=round(demanda_prom, 3),
        calendario=calendario,
        solapes=solapes,
        alertas=alertas,
    )
