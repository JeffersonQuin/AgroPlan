"""Corridas del agente y documento final del proyecto (paso 4).

El agente recibe un intake normalizado y devuelve una propuesta sin geometría. El
motor determinístico sigue siendo el único que calcula polígonos, sectores y red.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.agente import AgenteCorrida
from app.models.enums import EstadoCorrida
from app.models.proyecto import Proyecto, Terreno
from app.repository import agente_corrida as agente_corrida_repo
from app.repository import agente_fuente as agente_fuente_repo
from app.repository import agente_recomendacion as agente_recomendacion_repo
from app.repository import cultivo as cultivo_repo
from app.repository import proyecto as proyecto_repo
from app.repository import proyecto_cultivo as bloque_repo
from app.repository import terreno as terreno_repo
from app.schemas.agente import (
    BloqueGenerado,
    CorridaDetalleOut,
    CorridaIniciadaOut,
    CorridaOut,
    DisenoGenerado,
    EntradaAgente,
    FuenteOut,
    ProductoDeseado,
    RecomendacionOut,
    RecomendacionUpdate,
    ResultadoProyectoOut,
)
from app.services import geometria
from app.services import riego as riego_service

PROMPT_VERSION = "1.0.0"


class AgenteServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _terreno_requerido(db: Session, proyecto: Proyecto) -> Terreno:
    terreno = terreno_repo.get_by_proyecto(db, proyecto.id)
    if terreno is None:
        raise AgenteServiceError(
            422, "Primero define el terreno antes de ejecutar el agente"
        )
    return terreno


def _productos_desde_bloques(db: Session, proyecto: Proyecto) -> list[ProductoDeseado]:
    bloques = bloque_repo.list_by_proyecto(db, proyecto.id)
    if not bloques:
        raise AgenteServiceError(
            422, "Asigna al menos un cultivo antes de ejecutar el agente"
        )

    agrupados: dict[str, dict] = {}
    for bloque in bloques:
        actual = agrupados.setdefault(
            bloque.cultivo_codigo,
            {
                "prioridad": bloque.orden,
                "area": 0.0,
            },
        )
        actual["prioridad"] = min(actual["prioridad"], bloque.orden)
        actual["area"] += float(bloque.area_m2)

    productos: list[ProductoDeseado] = []
    for codigo, datos in sorted(agrupados.items(), key=lambda item: item[1]["prioridad"]):
        cultivo = cultivo_repo.get_by_codigo(db, codigo)
        productos.append(
            ProductoDeseado(
                nombre=cultivo.nombre if cultivo is not None else codigo,
                prioridad=datos["prioridad"],
                area_deseada_m2=round(datos["area"], 2) or None,
            )
        )
    return productos


def iniciar_corrida(
    db: Session, proyecto: Proyecto
) -> CorridaIniciadaOut:
    terreno = _terreno_requerido(db, proyecto)
    productos = _productos_desde_bloques(db, proyecto)

    entrada = EntradaAgente(
        proyecto_id=proyecto.id,
        productos=productos,
        area_m2=float(terreno.area_m2),
        suelo_codigo=terreno.suelo_codigo,
        fuente_agua=terreno.fuente_agua,
        caudal_efectivo_m3h=float(terreno.caudal_efectivo_m3h),
        caudal_origen=terreno.caudal_origen,
        zona=proyecto.zona,
        pendiente_pct=float(terreno.pendiente_pct),
    )

    corrida = AgenteCorrida(
        proyecto_id=proyecto.id,
        usuario_id=proyecto.usuario_id,
        estado=EstadoCorrida.PENDIENTE.value,
        entrada=entrada.model_dump(mode="json"),
        intake_hash=entrada.huella(),
        motor_version=riego_service.MOTOR_VERSION,
        prompt_version=PROMPT_VERSION,
    )
    corrida = agente_corrida_repo.create(db, corrida)

    # El proyecto apunta a su corrida vigente para que el front sepa qué polling
    # retomar al reabrir el wizard.
    proyecto.corrida_actual_id = corrida.id
    proyecto_repo.update(db, proyecto)

    return CorridaIniciadaOut(
        corrida_id=corrida.id,
        estado=corrida.estado,
        intake_hash=corrida.intake_hash,
    )


def listar_corridas(db: Session, proyecto: Proyecto) -> list[CorridaOut]:
    return [
        CorridaOut.model_validate(corrida)
        for corrida in agente_corrida_repo.list_by_proyecto(db, proyecto.id)
    ]


def obtener_corrida(
    db: Session, proyecto: Proyecto, corrida_id: uuid.UUID
) -> CorridaDetalleOut:
    corrida = agente_corrida_repo.get_by_id(db, corrida_id, proyecto.id)
    if corrida is None:
        raise AgenteServiceError(404, "Corrida del agente no encontrada")

    fuentes = [
        FuenteOut.model_validate(fuente)
        for fuente in agente_fuente_repo.list_by_corrida(db, corrida.id)
    ]
    detalle = CorridaDetalleOut.model_validate(corrida)
    return detalle.model_copy(update={"fuentes": fuentes})


def resultado_proyecto(db: Session, proyecto: Proyecto) -> ResultadoProyectoOut:
    try:
        diseno = riego_service.obtener_diseno(db, proyecto)
    except riego_service.RiegoServiceError as exc:
        raise AgenteServiceError(exc.status_code, exc.detail) from exc

    bloques = []
    for bloque in bloque_repo.list_by_proyecto(db, proyecto.id):
        cultivo = cultivo_repo.get_by_codigo(db, bloque.cultivo_codigo)
        try:
            puntos = geometria.normalizar_vertices(bloque.poligono.get("anillo", []))
        except (KeyError, TypeError, ValueError):
            continue
        bloques.append(
            BloqueGenerado(
                id=bloque.id,
                cultivo_codigo=bloque.cultivo_codigo,
                color=cultivo.color if cultivo is not None else "#4CAF50",
                poligono=geometria.poligono_dict(puntos),
                area_m2=float(bloque.area_m2),
                centroide=geometria.punto_dict(geometria.centroide(puntos)),
            )
        )

    return ResultadoProyectoOut(
        proyecto_id=proyecto.id,
        nombre=proyecto.nombre,
        estado=proyecto.estado,
        diseno=DisenoGenerado(
            bloques=bloques,
            sistema=diseno.sistema,
            sectores=diseno.sectores,
            red=diseno.red,
            computo=diseno.computo,
            advertencias=diseno.advertencias,
        ),
        advertencias=diseno.advertencias,
    )


# --------------------------------------------------------------------------- #
# Fuentes y recomendaciones de una corrida
# --------------------------------------------------------------------------- #


def _corrida_requerida(
    db: Session, proyecto: Proyecto, corrida_id: uuid.UUID
) -> AgenteCorrida:
    corrida = agente_corrida_repo.get_by_id(db, corrida_id, proyecto.id)
    if corrida is None:
        raise AgenteServiceError(404, "Corrida del agente no encontrada")
    return corrida


def listar_fuentes(
    db: Session, proyecto: Proyecto, corrida_id: uuid.UUID
) -> list[FuenteOut]:
    corrida = _corrida_requerida(db, proyecto, corrida_id)
    return [
        FuenteOut.model_validate(fuente)
        for fuente in agente_fuente_repo.list_by_corrida(db, corrida.id)
    ]


def listar_recomendaciones(
    db: Session, proyecto: Proyecto, corrida_id: uuid.UUID
) -> list[RecomendacionOut]:
    corrida = _corrida_requerida(db, proyecto, corrida_id)
    return [
        RecomendacionOut.model_validate(recomendacion)
        for recomendacion in agente_recomendacion_repo.list_by_corrida(
            db, corrida.id
        )
    ]


def actualizar_recomendacion(
    db: Session,
    proyecto: Proyecto,
    corrida_id: uuid.UUID,
    recomendacion_id: uuid.UUID,
    data: RecomendacionUpdate,
) -> RecomendacionOut:
    corrida = _corrida_requerida(db, proyecto, corrida_id)
    recomendacion = agente_recomendacion_repo.get_by_id(
        db, recomendacion_id, corrida.id
    )
    if recomendacion is None:
        raise AgenteServiceError(404, "Recomendación del agente no encontrada")

    recomendacion.aplicada = data.aplicada
    recomendacion.aplicada_en = (
        datetime.now(timezone.utc) if data.aplicada else None
    )
    recomendacion = agente_recomendacion_repo.update(db, recomendacion)
    return RecomendacionOut.model_validate(recomendacion)
