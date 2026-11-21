"""Endpoints de las recomendaciones emitidas por una corrida del agente."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_proyecto_actual
from app.models.proyecto import Proyecto
from app.schemas.agente import RecomendacionOut, RecomendacionUpdate
from app.services import agente as agente_service
from app.services.agente import AgenteServiceError

router = APIRouter(prefix="/proyectos", tags=["agente"])


@router.get(
    "/{proyecto_id}/agente/corridas/{corrida_id}/recomendaciones",
    response_model=list[RecomendacionOut],
)
def listar_recomendaciones(
    corrida_id: uuid.UUID,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> list[RecomendacionOut]:
    try:
        return agente_service.listar_recomendaciones(db, proyecto, corrida_id)
    except AgenteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.patch(
    "/{proyecto_id}/agente/corridas/{corrida_id}/recomendaciones/{recomendacion_id}",
    response_model=RecomendacionOut,
)
def actualizar_recomendacion(
    corrida_id: uuid.UUID,
    recomendacion_id: uuid.UUID,
    payload: RecomendacionUpdate,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> RecomendacionOut:
    try:
        return agente_service.actualizar_recomendacion(
            db, proyecto, corrida_id, recomendacion_id, payload
        )
    except AgenteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
