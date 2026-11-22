"""Motor determinístico del sistema de riego.

La red no la dibuja el cliente ni el LLM: se genera a partir de los parámetros del
sistema, la geometría del terreno y los bloques de cultivo. Los goteros no se
persisten uno por uno; se derivan de los laterales y de la separación del emisor.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import (
    Orientacion,
    OrigenCaudal,
    TipoNodo,
    TipoTramo,
)
from app.models.proyecto import Proyecto, Terreno
from app.models.riego import RedNodo, RedTramo, Sector, SectorBloque, SistemaRiego
from app.repository import proyecto_cultivo as bloque_repo
from app.repository import red_nodo as red_nodo_repo
from app.repository import red_tramo as red_tramo_repo
from app.repository import sector as sector_repo
from app.repository import sector_bloque as sector_bloque_repo
from app.repository import sistema_riego as sistema_riego_repo
from app.repository import terreno as terreno_repo
from app.schemas.comun import Advertencia
from app.schemas.riego import (
    ComputoOut,
    DisenoOut,
    EmisoresTramoOut,
    NodoOut,
    PreviewOut,
    RedOut,
    SectorBloqueIn,
    SectorBloqueOut,
    SectoresIn,
    SectorOut,
    SectorUpdate,
    SistemaRiegoIn,
    SistemaRiegoOut,
    TramoOut,
)
from app.services import geometria

MOTOR_VERSION = "1.0.0"
MAX_LATERALES_POR_SECTOR = 400
MAX_EMISORES_RESPUESTA = 20000
CAUDAL_MAXIMO = Decimal("999.999")


class RiegoServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _dec(valor: float, lugares: int = 2) -> Decimal:
    return Decimal(str(round(valor, lugares)))


def _longitud(valor: float) -> Decimal:
    """Longitud positiva: el CHECK de ``red_tramos`` exige ``longitud_m > 0``."""

    return max(_dec(valor), Decimal("0.01"))


def _sistema_requerido(db: Session, proyecto: Proyecto) -> SistemaRiego:
    sistema = sistema_riego_repo.get_by_proyecto(db, proyecto.id)
    if sistema is None:
        raise RiegoServiceError(
            404, "El proyecto todavía no tiene configuración de riego"
        )
    return sistema


def _borrar_diseno(db: Session, sistema: SistemaRiego) -> None:
    """Borra sectores y red: se vuelven a generar desde los parámetros vigentes."""

    ids_sectores = sector_repo.list_ids_by_sistema(db, sistema.id)
    sector_bloque_repo.delete_by_sector_ids(db, ids_sectores)
    red_nodo_repo.delete_by_sistema(db, sistema.id)
    red_tramo_repo.delete_by_sistema(db, sistema.id)
    sector_repo.delete_by_sistema(db, sistema.id)
    sistema.red_generada_en = None


def invalidar_diseno(db: Session, proyecto_id: uuid.UUID) -> None:
    """Marca como obsoleta la red si el proyecto cambió (terreno, bloques, etc.)."""

    sistema = sistema_riego_repo.get_by_proyecto(db, proyecto_id)
    if sistema is None:
        return
    _borrar_diseno(db, sistema)
    sistema_riego_repo.update(db, sistema)


def _terreno_requerido(db: Session, proyecto: Proyecto) -> Terreno:
    terreno = terreno_repo.get_by_proyecto(db, proyecto.id)
    if terreno is None:
        raise RiegoServiceError(
            422, "Primero define el terreno antes de configurar el riego"
        )
    return terreno


def _puntos_terreno(terreno: Terreno) -> list[geometria.Punto]:
    try:
        return geometria.normalizar_vertices(terreno.geometria.get("vertices", []))
    except (KeyError, TypeError, ValueError) as exc:
        raise RiegoServiceError(422, "El terreno no tiene geometría válida") from exc


def _punto_conexion(sistema: SistemaRiego) -> geometria.Punto:
    punto = sistema.punto_conexion or {}
    return (float(punto.get("x", 0)), float(punto.get("y", 0)))


def _sistema_out(sistema: SistemaRiego) -> SistemaRiegoOut:
    return SistemaRiegoOut.model_validate(sistema)


def _sector_out(sector: Sector) -> SectorOut:
    return SectorOut.model_validate(sector)


def _caudal_y_goteros(area: float, sistema: SistemaRiego) -> tuple[int, Decimal]:
    separacion = float(sistema.separacion_goteros_m) * float(
        sistema.separacion_laterales_m
    )
    if separacion <= 0:
        raise RiegoServiceError(422, "Las separaciones del emisor deben ser positivas")

    goteros = max(1, round(area / separacion))
    goteros = min(goteros, 32767)
    caudal = goteros * float(sistema.emisor_caudal_lh) / 1000.0
    return goteros, min(_dec(caudal, 3), CAUDAL_MAXIMO)


def _laterales_sector(sistema: SistemaRiego, sector: Sector) -> list[list[geometria.Punto]]:
    try:
        puntos = geometria.normalizar_vertices(sector.poligono.get("anillo", []))
    except (KeyError, TypeError, ValueError):
        return []

    x_min, y_min, x_max, y_max = geometria.caja(puntos)
    ancho = x_max - x_min
    alto = y_max - y_min
    separacion = float(sistema.separacion_laterales_m)
    if separacion <= 0:
        separacion = 1.0

    if sistema.orientacion in (Orientacion.ESTE_OESTE.value, Orientacion.OESTE_ESTE.value):
        if alto <= 1e-6 or ancho <= 1e-6:
            return []
        cantidad = max(1, int(alto / separacion))
        cantidad = min(cantidad, MAX_LATERALES_POR_SECTOR)
        paso = alto / cantidad
        return [
            [
                (x_min, y_min + paso / 2 + indice * paso),
                (x_max, y_min + paso / 2 + indice * paso),
            ]
            for indice in range(cantidad)
        ]

    if ancho <= 1e-6 or alto <= 1e-6:
        return []
    cantidad = max(1, int(ancho / separacion))
    cantidad = min(cantidad, MAX_LATERALES_POR_SECTOR)
    paso = ancho / cantidad
    return [
        [
            (x_min + paso / 2 + indice * paso, y_min),
            (x_min + paso / 2 + indice * paso, y_max),
        ]
        for indice in range(cantidad)
    ]


def _centroide_sector(sector: Sector) -> geometria.Punto:
    puntos = geometria.normalizar_vertices(sector.poligono.get("anillo", []))
    return geometria.centroide(puntos)


def _poligono_franja(
    terreno: Terreno, indice: int, total: int
) -> tuple[dict, float]:
    puntos = _puntos_terreno(terreno)
    x_min, y_min, x_max, y_max = geometria.caja(puntos)
    ancho = x_max - x_min
    if ancho <= 1e-6 or total <= 0:
        return geometria.poligono_dict(puntos), float(terreno.area_m2)

    x0 = x_min + ancho * indice / total
    x1 = x_min + ancho * (indice + 1) / total
    franja = geometria.rectangulo(x0, y_min, x1, y_max)
    return geometria.poligono_dict(franja), geometria.area_poligono(franja)


def _poligono_desde_bloques(bloques: list) -> dict | None:
    puntos: list[geometria.Punto] = []
    for bloque in bloques:
        try:
            puntos.extend(
                geometria.normalizar_vertices(bloque.poligono.get("anillo", []))
            )
        except (KeyError, TypeError, ValueError):
            continue
    if not puntos:
        return None
    x_min, y_min, x_max, y_max = geometria.caja(puntos)
    return geometria.poligono_dict(
        geometria.rectangulo(x_min, y_min, x_max, y_max)
    )


def _crear_sector(
    db: Session,
    sistema: SistemaRiego,
    *,
    numero: int,
    etiqueta: str | None,
    poligono: dict,
    area: float,
    secuencia: int,
    bloques: list,
) -> Sector:
    goteros, caudal = _caudal_y_goteros(area, sistema)
    sector = Sector(
        sistema_id=sistema.id,
        numero=numero,
        etiqueta=etiqueta,
        poligono=poligono,
        area_m2=_dec(area),
        num_goteros=goteros,
        caudal_m3h=caudal,
        secuencia=secuencia,
    )
    sector = sector_repo.add(db, sector)
    for bloque in bloques:
        sector_bloque_repo.add(
            db,
            SectorBloque(
                sector_id=sector.id,
                proyecto_cultivo_id=bloque.id,
                area_m2=bloque.area_m2,
            ),
        )
    return sector


def _generar_sectores_auto(
    db: Session,
    sistema: SistemaRiego,
    terreno: Terreno,
    bloques: list,
) -> list[Sector]:
    total = sistema.num_sectores
    puntos = _puntos_terreno(terreno)
    x_min, _, x_max, _ = geometria.caja(puntos)
    ancho = x_max - x_min

    grupos: list[list] = [[] for _ in range(total)]
    for bloque in bloques:
        try:
            centro = geometria.centroide(
                geometria.normalizar_vertices(bloque.poligono.get("anillo", []))
            )
        except (KeyError, TypeError, ValueError):
            indice = 0
        else:
            indice = 0 if ancho <= 1e-6 else int((centro[0] - x_min) / ancho * total)
            indice = max(0, min(total - 1, indice))
        grupos[indice].append(bloque)

    area_terreno = float(terreno.area_m2)
    sectores: list[Sector] = []
    for indice, grupo in enumerate(grupos):
        poligono, _ = _poligono_franja(terreno, indice, total)
        area = max(area_terreno / total, sum(float(b.area_m2) for b in grupo))
        sectores.append(
            _crear_sector(
                db,
                sistema,
                numero=indice + 1,
                etiqueta=f"Sector {indice + 1}",
                poligono=poligono,
                area=area,
                secuencia=indice + 1,
                bloques=grupo,
            )
        )
    return sectores


def _generar_sectores_desde_payload(
    db: Session,
    sistema: SistemaRiego,
    terreno: Terreno,
    bloques: list,
    data: SectoresIn,
) -> list[Sector]:
    por_id = {bloque.id: bloque for bloque in bloques}
    numeros = [sector.numero for sector in data.sectores]
    if len(set(numeros)) != len(numeros):
        raise RiegoServiceError(422, "Los números de sector no pueden repetirse")

    # Un bloque puede repartirse entre varios sectores: el área del vínculo se divide
    # entre las apariciones para no duplicar superficie.
    apariciones: dict[uuid.UUID, int] = {}
    for sector_in in data.sectores:
        for bloque_id in set(sector_in.cultivo_ids):
            apariciones[bloque_id] = apariciones.get(bloque_id, 0) + 1

    sectores: list[Sector] = []
    for indice, sector_in in enumerate(data.sectores):
        ids = list(dict.fromkeys(sector_in.cultivo_ids))
        grupo = []
        for bloque_id in ids:
            bloque = por_id.get(bloque_id)
            if bloque is None:
                raise RiegoServiceError(
                    422, f"El bloque {bloque_id} no pertenece a este proyecto"
                )
            grupo.append(bloque)

        area_bloques = sum(
            float(bloque.area_m2) / apariciones.get(bloque.id, 1) for bloque in grupo
        )
        area = area_bloques if grupo else float(sector_in.area_m2)
        poligono = _poligono_desde_bloques(grupo)
        if poligono is None:
            poligono, _ = _poligono_franja(terreno, indice, len(data.sectores))

        sector = _crear_sector(
            db,
            sistema,
            numero=sector_in.numero,
            etiqueta=sector_in.etiqueta or f"Sector {sector_in.numero}",
            poligono=poligono,
            area=max(area, 0.01),
            secuencia=sector_in.secuencia,
            bloques=[],
        )
        for bloque in grupo:
            sector_bloque_repo.add(
                db,
                SectorBloque(
                    sector_id=sector.id,
                    proyecto_cultivo_id=bloque.id,
                    area_m2=_dec(
                        float(bloque.area_m2) / apariciones.get(bloque.id, 1)
                    ),
                ),
            )
        sectores.append(sector)

    if len(data.sectores) != sistema.num_sectores:
        sistema.num_sectores = len(data.sectores)
        sistema.parametros_version += 1

    return sectores


def _generar_red(
    db: Session,
    sistema: SistemaRiego,
    terreno: Terreno,
    sectores: list[Sector],
) -> None:
    puntos_terreno = _puntos_terreno(terreno)
    centro = geometria.centro_caja(puntos_terreno)
    conexion = _punto_conexion(sistema)
    caudal_terreno = min(_dec(float(terreno.caudal_efectivo_m3h), 3), CAUDAL_MAXIMO)

    if sistema.tanque_l is not None:
        red_nodo_repo.add(
            db,
            RedNodo(
                sistema_id=sistema.id,
                tipo=TipoNodo.TANQUE.value,
                geometria=geometria.punto_dict(conexion),
                atributos={"capacidad_l": float(sistema.tanque_l)},
            ),
        )

    red_nodo_repo.add(
        db,
        RedNodo(
            sistema_id=sistema.id,
            tipo=TipoNodo.BOMBA.value,
            geometria=geometria.punto_dict(conexion),
            atributos={"bomba_hp": float(sistema.bomba_hp)},
        ),
    )
    red_nodo_repo.add(
        db,
        RedNodo(
            sistema_id=sistema.id,
            tipo=TipoNodo.CABEZAL.value,
            geometria=geometria.punto_dict(centro),
            atributos={"diametro_principal_mm": sistema.diametro_principal_mm},
        ),
    )

    inicio, fin = geometria.segmento_desplazado(conexion, centro)
    red_tramo_repo.add(
        db,
        RedTramo(
            sistema_id=sistema.id,
            tipo=TipoTramo.PRINCIPAL.value,
            diametro_mm=sistema.diametro_principal_mm,
            longitud_m=_longitud(geometria.distancia(inicio, fin)),
            geometria={
                "puntos": [
                    [round(inicio[0], 4), round(inicio[1], 4)],
                    [round(fin[0], 4), round(fin[1], 4)],
                ]
            },
            caudal_m3h=caudal_terreno,
            orden=1,
        ),
    )

    diametro_secundario = max(16, min(32, sistema.diametro_principal_mm - 16))

    for sector in sectores:
        centro_sector = _centroide_sector(sector)
        inicio, fin = geometria.segmento_desplazado(centro, centro_sector)
        red_tramo_repo.add(
            db,
            RedTramo(
                sistema_id=sistema.id,
                sector_id=sector.id,
                tipo=TipoTramo.SECUNDARIO.value,
                diametro_mm=diametro_secundario,
                longitud_m=_longitud(geometria.distancia(inicio, fin)),
                geometria={
                    "puntos": [
                        [round(inicio[0], 4), round(inicio[1], 4)],
                        [round(fin[0], 4), round(fin[1], 4)],
                    ]
                },
                caudal_m3h=sector.caudal_m3h,
                orden=sector.numero,
            ),
        )

        red_nodo_repo.add(
            db,
            RedNodo(
                sistema_id=sistema.id,
                tipo=TipoNodo.VALVULA.value,
                geometria=geometria.punto_dict(centro_sector),
                atributos={"sector_id": str(sector.id), "numero": sector.numero},
            ),
        )

        laterales = _laterales_sector(sistema, sector)
        if not laterales:
            continue
        caudal_lateral = min(
            _dec(float(sector.caudal_m3h) / len(laterales), 3), CAUDAL_MAXIMO
        )
        for orden, (inicio, fin) in enumerate(laterales, start=1):
            red_tramo_repo.add(
                db,
                RedTramo(
                    sistema_id=sistema.id,
                    sector_id=sector.id,
                    tipo=TipoTramo.LATERAL.value,
                    diametro_mm=16,
                    longitud_m=_longitud(geometria.distancia(inicio, fin)),
                    geometria={
                        "puntos": [
                            [round(inicio[0], 4), round(inicio[1], 4)],
                            [round(fin[0], 4), round(fin[1], 4)],
                        ]
                    },
                    caudal_m3h=caudal_lateral,
                    orden=orden,
                ),
            )

    sistema.red_generada_en = datetime.now(timezone.utc)


def _emisores_desde_tramos(
    sistema: SistemaRiego, tramos: list[RedTramo]
) -> list[EmisoresTramoOut]:
    separacion = float(sistema.separacion_goteros_m)
    salida: list[EmisoresTramoOut] = []
    total = 0

    for tramo in tramos:
        if tramo.tipo != TipoTramo.LATERAL.value:
            continue
        puntos_tramo = tramo.puntos
        if len(puntos_tramo) < 2:
            continue

        puntos: list[geometria.Punto] = []
        for indice in range(len(puntos_tramo) - 1):
            segmento = geometria.puntos_interpolados(
                puntos_tramo[indice], puntos_tramo[indice + 1], separacion
            )
            if indice > 0 and segmento and puntos and segmento[0] == puntos[-1]:
                segmento = segmento[1:]
            puntos.extend(segmento)
            if len(puntos) >= MAX_EMISORES_RESPUESTA:
                break

        salida.append(
            EmisoresTramoOut(
                tramo_id=tramo.id,
                separacion_m=separacion,
                puntos=puntos[:MAX_EMISORES_RESPUESTA],
            )
        )
        total += len(puntos)
        if total >= MAX_EMISORES_RESPUESTA:
            break

    return salida


def _red_out(db: Session, sistema: SistemaRiego) -> RedOut:
    nodos = red_nodo_repo.list_by_sistema(db, sistema.id)
    tramos = red_tramo_repo.list_by_sistema(db, sistema.id)
    return RedOut(
        nodos=[NodoOut.model_validate(nodo) for nodo in nodos],
        tramos=[TramoOut.model_validate(tramo) for tramo in tramos],
        emisores=_emisores_desde_tramos(sistema, tramos),
    )


def _computo(sectores: list[Sector], tramos: list[RedTramo], nodos: list[RedNodo]) -> ComputoOut:
    valvulas = sum(1 for nodo in nodos if nodo.tipo == TipoNodo.VALVULA.value)
    return ComputoOut(
        tuberia_m=round(sum(float(tramo.longitud_m) for tramo in tramos), 2),
        goteros_u=sum(int(sector.num_goteros) for sector in sectores),
        valvulas_u=valvulas or len(sectores),
    )


def _advertencias_diseno(
    terreno: Terreno, bloques: list, sectores: list[Sector]
) -> list[Advertencia]:
    alertas: list[Advertencia] = []
    if not bloques:
        alertas.append(
            Advertencia(
                codigo="sin_cultivos",
                mensaje="Asigna al menos un cultivo antes de generar la red de riego.",
                bloqueante=True,
            )
        )
        return alertas

    area_terreno = float(terreno.area_m2)
    area_bloques = sum(float(bloque.area_m2) for bloque in bloques)
    if area_bloques > area_terreno + 0.01:
        alertas.append(
            Advertencia(
                codigo="area_excedida",
                mensaje=(
                    "Los bloques de cultivo superan la superficie del terreno; la red "
                    "se generó igual, pero revisa el reparto del paso 2."
                ),
                bloqueante=False,
                campo="area_m2",
            )
        )

    area_sectores = sum(float(sector.area_m2) for sector in sectores)
    if area_sectores > area_terreno + 0.01:
        alertas.append(
            Advertencia(
                codigo="sectores_exceden_terreno",
                mensaje=(
                    "La suma de los sectores supera la superficie del terreno. Ajusta "
                    "la cantidad de sectores o el reparto de cultivos."
                ),
                bloqueante=False,
                campo="sectores",
            )
        )

    caudal_efectivo = float(terreno.caudal_efectivo_m3h)
    for sector in sectores:
        if float(sector.caudal_m3h) > caudal_efectivo + 0.001:
            alertas.append(
                Advertencia(
                    codigo="caudal_sector_excedido",
                    mensaje=(
                        f"El sector {sector.numero} requiere "
                        f"{float(sector.caudal_m3h):.2f} m³/h y el caudal disponible es "
                        f"{caudal_efectivo:.2f} m³/h. Reduce el área o aumenta el caudal."
                    ),
                    bloqueante=False,
                    campo="caudal_efectivo_m3h",
                )
            )
            break

    if terreno.caudal_origen == OrigenCaudal.ASUMIDO.value:
        alertas.append(
            Advertencia(
                codigo="caudal_asumido",
                mensaje=(
                    "El caudal usado es un valor de referencia asignado por el sistema "
                    "según la fuente de agua; confírmalo con una medición real."
                ),
                campo="caudal_disponible_m3h",
            )
        )

    return alertas


def obtener_config(db: Session, proyecto: Proyecto) -> SistemaRiegoOut:
    return _sistema_out(_sistema_requerido(db, proyecto))


def upsert_config(
    db: Session, proyecto: Proyecto, data: SistemaRiegoIn
) -> SistemaRiegoOut:
    terreno = _terreno_requerido(db, proyecto)
    if data.fuente_agua.value != terreno.fuente_agua:
        raise RiegoServiceError(
            422,
            "La fuente de agua del riego debe coincidir con la del terreno",
        )

    valores = {
        "tipo": data.tipo.value,
        "fuente_agua": data.fuente_agua.value,
        "tanque_l": _dec(data.tanque_l, 1) if data.tanque_l is not None else None,
        "bomba_hp": _dec(data.bomba_hp, 1),
        "diametro_principal_mm": data.diametro_principal_mm,
        "emisor_tipo": data.emisor.tipo,
        "emisor_caudal_lh": _dec(data.emisor.caudal_lh, 2),
        "separacion_goteros_m": _dec(data.emisor.separacion_m, 2),
        "separacion_laterales_m": _dec(data.separacion_laterales_m, 2),
        "orientacion": data.orientacion.value,
        "punto_conexion": data.punto_conexion.model_dump(),
        "num_sectores": data.num_sectores,
    }

    sistema = sistema_riego_repo.get_by_proyecto(db, proyecto.id)
    if sistema is None:
        sistema = SistemaRiego(
            proyecto_id=proyecto.id,
            parametros_version=1,
            **valores,
        )
        sistema = sistema_riego_repo.create(db, sistema)
        return _sistema_out(sistema)

    cambio = any(getattr(sistema, campo) != valor for campo, valor in valores.items())
    if cambio:
        _borrar_diseno(db, sistema)
        sistema.parametros_version += 1

    for campo, valor in valores.items():
        setattr(sistema, campo, valor)

    sistema = sistema_riego_repo.update(db, sistema)
    return _sistema_out(sistema)


def preview(db: Session, proyecto: Proyecto) -> PreviewOut:
    sistema = _sistema_requerido(db, proyecto)
    terreno = _terreno_requerido(db, proyecto)
    bloques = bloque_repo.list_by_proyecto(db, proyecto.id)

    caudal_efectivo = float(terreno.caudal_efectivo_m3h)
    num_sectores = max(1, sistema.num_sectores)
    caudal_sector = caudal_efectivo / num_sectores
    caudal_total = caudal_sector * num_sectores

    demanda_total = sum(
        float(bloque.area_m2) * float(bloque.demanda_l_m2_dia) for bloque in bloques
    )
    tiempo_riego = (
        math.ceil(demanda_total / (caudal_efectivo * 1000.0) * 60.0)
        if caudal_efectivo > 0
        else 0
    )

    presion = round(1.0 + 0.5 * float(sistema.bomba_hp), 2)
    autonomia = (
        float(sistema.tanque_l) / demanda_total
        if sistema.tanque_l is not None and demanda_total > 0
        else None
    )

    puntos_terreno = _puntos_terreno(terreno)
    centro = geometria.centro_caja(puntos_terreno)
    conexion = _punto_conexion(sistema)
    x_min, y_min, x_max, y_max = geometria.caja(puntos_terreno)
    diagonal = math.hypot(x_max - x_min, y_max - y_min)
    area_asignada = sum(float(bloque.area_m2) for bloque in bloques)
    separacion_goteros = max(float(sistema.separacion_goteros_m), 0.01)
    separacion_laterales = max(float(sistema.separacion_laterales_m), 0.01)

    tuberia = (
        geometria.distancia(conexion, centro)
        + num_sectores * diagonal / 2.0
        + area_asignada / separacion_laterales
    )
    goteros = round(area_asignada / (separacion_goteros * separacion_laterales))

    advertencias: list[Advertencia] = []
    if not bloques:
        advertencias.append(
            Advertencia(
                codigo="sin_cultivos",
                mensaje="Asigna al menos un cultivo para calcular la demanda de riego.",
                bloqueante=True,
            )
        )
    if tiempo_riego > 24 * 60:
        advertencias.append(
            Advertencia(
                codigo="tiempo_riego_excesivo",
                mensaje=(
                    "El tiempo de riego calculado supera 24 horas. Aumenta el caudal, "
                    "reduce la superficie o revisa la demanda de los cultivos."
                ),
                campo="caudal_efectivo_m3h",
            )
        )
    if area_asignada > float(terreno.area_m2) + 0.01:
        advertencias.append(
            Advertencia(
                codigo="area_excedida",
                mensaje="La superficie asignada a cultivos supera la del terreno.",
                bloqueante=True,
                campo="area_m2",
            )
        )

    return PreviewOut(
        caudal_efectivo_m3h=round(caudal_efectivo, 3),
        caudal_origen=terreno.caudal_origen,
        caudal_sector_m3h=round(caudal_sector, 3),
        caudal_total_m3h=round(caudal_total, 3),
        presion_bar=presion,
        tiempo_riego_min=tiempo_riego,
        autonomia_dias=round(autonomia, 2) if autonomia is not None else None,
        computo=ComputoOut(
            tuberia_m=round(tuberia, 2),
            goteros_u=max(goteros, 0),
            valvulas_u=num_sectores,
        ),
        advertencias=advertencias,
    )


def generar(
    db: Session, proyecto: Proyecto, data: SectoresIn | None = None
) -> DisenoOut:
    sistema = _sistema_requerido(db, proyecto)
    terreno = _terreno_requerido(db, proyecto)
    bloques = bloque_repo.list_by_proyecto(db, proyecto.id)
    if not bloques:
        raise RiegoServiceError(
            422, "Asigna al menos un cultivo antes de generar la red de riego"
        )

    _borrar_diseno(db, sistema)

    if data is not None:
        sectores = _generar_sectores_desde_payload(
            db, sistema, terreno, bloques, data
        )
    else:
        sectores = _generar_sectores_auto(db, sistema, terreno, bloques)

    _generar_red(db, sistema, terreno, sectores)
    sistema_riego_repo.update(db, sistema)

    sectores_db = sector_repo.list_by_sistema(db, sistema.id)
    tramos = red_tramo_repo.list_by_sistema(db, sistema.id)
    nodos = red_nodo_repo.list_by_sistema(db, sistema.id)
    red = RedOut(
        nodos=[NodoOut.model_validate(nodo) for nodo in nodos],
        tramos=[TramoOut.model_validate(tramo) for tramo in tramos],
        emisores=_emisores_desde_tramos(sistema, tramos),
    )

    return DisenoOut(
        sistema=_sistema_out(sistema),
        sectores=[_sector_out(sector) for sector in sectores_db],
        red=red,
        computo=_computo(sectores_db, tramos, nodos),
        advertencias=_advertencias_diseno(terreno, bloques, sectores_db),
    )


def obtener_diseno(db: Session, proyecto: Proyecto) -> DisenoOut:
    sistema = _sistema_requerido(db, proyecto)
    if sistema.red_generada_en is None:
        raise RiegoServiceError(404, "La red de riego todavía no fue generada")

    terreno = _terreno_requerido(db, proyecto)
    bloques = bloque_repo.list_by_proyecto(db, proyecto.id)
    sectores = sector_repo.list_by_sistema(db, sistema.id)
    tramos = red_tramo_repo.list_by_sistema(db, sistema.id)
    nodos = red_nodo_repo.list_by_sistema(db, sistema.id)
    red = RedOut(
        nodos=[NodoOut.model_validate(nodo) for nodo in nodos],
        tramos=[TramoOut.model_validate(tramo) for tramo in tramos],
        emisores=_emisores_desde_tramos(sistema, tramos),
    )

    return DisenoOut(
        sistema=_sistema_out(sistema),
        sectores=[_sector_out(sector) for sector in sectores],
        red=red,
        computo=_computo(sectores, tramos, nodos),
        advertencias=_advertencias_diseno(terreno, bloques, sectores),
    )


def obtener_red(db: Session, proyecto: Proyecto) -> RedOut:
    sistema = _sistema_requerido(db, proyecto)
    return _red_out(db, sistema)


# --------------------------------------------------------------------------- #
# Sectores
# --------------------------------------------------------------------------- #


def _sector_requerido(
    db: Session, sistema: SistemaRiego, sector_id: uuid.UUID
) -> Sector:
    sector = sector_repo.get_by_id(db, sector_id, sistema.id)
    if sector is None:
        raise RiegoServiceError(404, "Sector de riego no encontrado")
    return sector


def _recalcular_sector(
    db: Session, sistema: SistemaRiego, sector: Sector
) -> None:
    area = float(sector_bloque_repo.sum_area_by_sector(db, sector.id))
    if area <= 0:
        return
    goteros, caudal = _caudal_y_goteros(area, sistema)
    sector.area_m2 = _dec(area)
    sector.num_goteros = goteros
    sector.caudal_m3h = caudal
    sector_repo.update(db, sector)


def listar_sectores(db: Session, proyecto: Proyecto) -> list[SectorOut]:
    sistema = _sistema_requerido(db, proyecto)
    return [
        _sector_out(sector)
        for sector in sector_repo.list_by_sistema(db, sistema.id)
    ]


def obtener_sector(
    db: Session, proyecto: Proyecto, sector_id: uuid.UUID
) -> SectorOut:
    sistema = _sistema_requerido(db, proyecto)
    return _sector_out(_sector_requerido(db, sistema, sector_id))


def actualizar_sector(
    db: Session,
    proyecto: Proyecto,
    sector_id: uuid.UUID,
    data: SectorUpdate,
) -> SectorOut:
    sistema = _sistema_requerido(db, proyecto)
    sector = _sector_requerido(db, sistema, sector_id)
    campos = data.model_fields_set
    if "etiqueta" in campos:
        sector.etiqueta = data.etiqueta
    if "secuencia" in campos and data.secuencia is not None:
        sector.secuencia = data.secuencia
    sector = sector_repo.update(db, sector)
    return _sector_out(sector)


# --------------------------------------------------------------------------- #
# Reparto de bloques entre sectores
# --------------------------------------------------------------------------- #


def listar_sector_bloques(
    db: Session, proyecto: Proyecto, sector_id: uuid.UUID
) -> list[SectorBloqueOut]:
    sistema = _sistema_requerido(db, proyecto)
    sector = _sector_requerido(db, sistema, sector_id)
    return [
        SectorBloqueOut.model_validate(vinculo)
        for vinculo in sector_bloque_repo.list_by_sector(db, sector.id)
    ]


def obtener_sector_bloque(
    db: Session,
    proyecto: Proyecto,
    sector_id: uuid.UUID,
    vinculo_id: uuid.UUID,
) -> SectorBloqueOut:
    sistema = _sistema_requerido(db, proyecto)
    sector = _sector_requerido(db, sistema, sector_id)
    vinculo = sector_bloque_repo.get_by_id(db, vinculo_id, sector.id)
    if vinculo is None:
        raise RiegoServiceError(404, "Vínculo sector-bloque no encontrado")
    return SectorBloqueOut.model_validate(vinculo)


def crear_sector_bloque(
    db: Session,
    proyecto: Proyecto,
    sector_id: uuid.UUID,
    data: SectorBloqueIn,
) -> SectorBloqueOut:
    sistema = _sistema_requerido(db, proyecto)
    sector = _sector_requerido(db, sistema, sector_id)
    bloque = bloque_repo.get_by_id(db, data.proyecto_cultivo_id, proyecto.id)
    if bloque is None:
        raise RiegoServiceError(
            422, "El bloque de cultivo no pertenece a este proyecto"
        )
    if sector_bloque_repo.get_by_sector_and_bloque(db, sector.id, bloque.id):
        raise RiegoServiceError(
            409, "El bloque ya está asignado a este sector"
        )

    vinculo = sector_bloque_repo.add(
        db,
        SectorBloque(
            sector_id=sector.id,
            proyecto_cultivo_id=bloque.id,
            area_m2=_dec(data.area_m2),
        ),
    )
    _recalcular_sector(db, sistema, sector)
    return SectorBloqueOut.model_validate(vinculo)


def eliminar_sector_bloque(
    db: Session,
    proyecto: Proyecto,
    sector_id: uuid.UUID,
    vinculo_id: uuid.UUID,
) -> None:
    sistema = _sistema_requerido(db, proyecto)
    sector = _sector_requerido(db, sistema, sector_id)
    vinculo = sector_bloque_repo.get_by_id(db, vinculo_id, sector.id)
    if vinculo is None:
        raise RiegoServiceError(404, "Vínculo sector-bloque no encontrado")
    sector_bloque_repo.delete(db, vinculo)
    _recalcular_sector(db, sistema, sector)


# --------------------------------------------------------------------------- #
# Red generada
# --------------------------------------------------------------------------- #


def listar_tramos(db: Session, proyecto: Proyecto) -> list[TramoOut]:
    sistema = _sistema_requerido(db, proyecto)
    return [
        TramoOut.model_validate(tramo)
        for tramo in red_tramo_repo.list_by_sistema(db, sistema.id)
    ]


def obtener_tramo(
    db: Session, proyecto: Proyecto, tramo_id: uuid.UUID
) -> TramoOut:
    sistema = _sistema_requerido(db, proyecto)
    tramo = red_tramo_repo.get_by_id(db, tramo_id, sistema.id)
    if tramo is None:
        raise RiegoServiceError(404, "Tramo de red no encontrado")
    return TramoOut.model_validate(tramo)


def listar_nodos(db: Session, proyecto: Proyecto) -> list[NodoOut]:
    sistema = _sistema_requerido(db, proyecto)
    return [
        NodoOut.model_validate(nodo)
        for nodo in red_nodo_repo.list_by_sistema(db, sistema.id)
    ]


def obtener_nodo(
    db: Session, proyecto: Proyecto, nodo_id: uuid.UUID
) -> NodoOut:
    sistema = _sistema_requerido(db, proyecto)
    nodo = red_nodo_repo.get_by_id(db, nodo_id, sistema.id)
    if nodo is None:
        raise RiegoServiceError(404, "Nodo de red no encontrado")
    return NodoOut.model_validate(nodo)
