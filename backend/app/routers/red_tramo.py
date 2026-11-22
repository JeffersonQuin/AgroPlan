"""Endpoints de los tramos de la red de riego."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_proyecto_actual
from app.models.proyecto import Proyecto
from app.schemas.riego import TramoOut
from app.services import riego as riego_service
from app.services.riego import RiegoServiceError

router = APIRouter(prefix="/proyectos", tags=["riego"])


@router.get("/{proyecto_id}/riego/tramos", response_model=list[TramoOut])
def listar_tramos(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> list[TramoOut]:
    try:
        return riego_service.listar_tramos(db, proyecto)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get(
    "/{proyecto_id}/riego/tramos/{tramo_id}", response_model=TramoOut
)
def obtener_tramo(
    tramo_id: uuid.UUID,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> TramoOut:
    try:
        return riego_service.obtener_tramo(db, proyecto, tramo_id)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
