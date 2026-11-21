"""Endpoints de las corridas del agente de recomendaciones."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_proyecto_actual
from app.models.proyecto import Proyecto
from app.schemas.agente import (
    CorridaDetalleOut,
    CorridaIniciadaOut,
    CorridaOut,
)
from app.services import agente as agente_service
from app.services.agente import AgenteServiceError

router = APIRouter(prefix="/proyectos", tags=["agente"])


@router.post(
    "/{proyecto_id}/agente/corridas",
    response_model=CorridaIniciadaOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def iniciar_corrida(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> CorridaIniciadaOut:
    try:
        return agente_service.iniciar_corrida(db, proyecto)
    except AgenteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{proyecto_id}/agente/corridas", response_model=list[CorridaOut])
def listar_corridas(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> list[CorridaOut]:
    return agente_service.listar_corridas(db, proyecto)


@router.get(
    "/{proyecto_id}/agente/corridas/{corrida_id}",
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
