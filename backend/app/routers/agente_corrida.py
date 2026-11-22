"""Endpoints de las corridas del agente de recomendaciones.

``POST /proyectos/{id}/agente`` responde 202 con el ``corrida_id`` y ejecuta el agente
en segundo plano: el request nunca espera al modelo. El front hace polling hasta
``estado: ok`` y recién ahí puede pedir ``aplicar``.
"""

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_proyecto_actual
from app.models.proyecto import Proyecto
from app.models.usuario import Usuario
from app.schemas.agente import (
    CorridaDetalleOut,
    CorridaIniciadaOut,
    CorridaIniciarIn,
    CorridaOut,
    ResultadoProyectoOut,
)
from app.services import agente as agente_service
from app.services.agente import AgenteServiceError

router = APIRouter(tags=["agente"])


def _iniciar(
    proyecto: Proyecto,
    background: BackgroundTasks,
    response: Response,
    db: Session,
    cuerpo: CorridaIniciarIn | None = None,
) -> CorridaIniciadaOut:
    try:
        inicio = agente_service.iniciar_corrida(
            db,
            proyecto,
            productos=cuerpo.productos if cuerpo is not None else None,
            siembra=cuerpo.siembra if cuerpo is not None else None,
            restricciones=cuerpo.restricciones if cuerpo is not None else None,
            regenerar=cuerpo.regenerar if cuerpo is not None else False,
        )
    except AgenteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if inicio.creada:
        background.add_task(
            agente_service.ejecutar_corrida, db, inicio.corrida_id, proyecto.id
        )
    else:
        # Mismo intake con corrida terminada: se reutiliza y no se vuelve a gastar.
        response.status_code = status.HTTP_200_OK

    return CorridaIniciadaOut(
        corrida_id=inicio.corrida_id,
        estado=inicio.estado,
        intake_hash=inicio.intake_hash,
    )


@router.post(
    "/proyectos/{proyecto_id}/agente",
    response_model=CorridaIniciadaOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def iniciar_corrida(
    background: BackgroundTasks,
    response: Response,
    cuerpo: CorridaIniciarIn | None = None,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> CorridaIniciadaOut:
    return _iniciar(proyecto, background, response, db, cuerpo)


@router.post(
    "/proyectos/{proyecto_id}/agente/corridas",
    response_model=CorridaIniciadaOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def iniciar_corrida_por_corridas(
    background: BackgroundTasks,
    response: Response,
    cuerpo: CorridaIniciarIn | None = None,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> CorridaIniciadaOut:
    return _iniciar(proyecto, background, response, db, cuerpo)


@router.get("/proyectos/{proyecto_id}/agente/corridas", response_model=list[CorridaOut])
def listar_corridas(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> list[CorridaOut]:
    return agente_service.listar_corridas(db, proyecto)


@router.get(
    "/proyectos/{proyecto_id}/agente/corridas/{corrida_id}",
    response_model=CorridaDetalleOut,
)
def obtener_corrida(
    corrida_id: uuid.UUID,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> CorridaDetalleOut:
    try:
        return agente_service.obtener_corrida(db, proyecto, corrida_id)
    except AgenteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/agente/corridas/{corrida_id}", response_model=CorridaDetalleOut)
def obtener_corrida_global(
    corrida_id: uuid.UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CorridaDetalleOut:
    try:
        return agente_service.obtener_corrida_del_usuario(db, current_user, corrida_id)
    except AgenteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/agente/corridas/{corrida_id}/aplicar", response_model=ResultadoProyectoOut)
def aplicar_corrida_global(
    corrida_id: uuid.UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResultadoProyectoOut:
    try:
        return agente_service.aplicar_corrida_del_usuario(db, current_user, corrida_id)
    except AgenteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post(
    "/proyectos/{proyecto_id}/agente/corridas/{corrida_id}/aplicar",
    response_model=ResultadoProyectoOut,
)
def aplicar_corrida(
    corrida_id: uuid.UUID,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> ResultadoProyectoOut:
    try:
        return agente_service.aplicar_corrida(db, proyecto, corrida_id)
    except AgenteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
