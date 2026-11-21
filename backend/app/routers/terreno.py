"""Endpoints del paso 1: terreno, geometría derivada y caudal efectivo."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_proyecto_actual
from app.models.proyecto import Proyecto
from app.schemas.proyecto import TerrenoIn, TerrenoOut, TerrenoUpdate
from app.services import terreno as terreno_service
from app.services.terreno import TerrenoServiceError

router = APIRouter(prefix="/proyectos", tags=["terreno"])


@router.get("/{proyecto_id}/terreno", response_model=TerrenoOut)
def obtener_terreno(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> TerrenoOut:
    try:
        return terreno_service.obtener_terreno(db, proyecto)
    except TerrenoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.put("/{proyecto_id}/terreno", response_model=TerrenoOut)
def crear_terreno(
    payload: TerrenoIn,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> TerrenoOut:
    try:
        return terreno_service.crear_terreno(db, proyecto, payload)
    except TerrenoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.patch("/{proyecto_id}/terreno", response_model=TerrenoOut)
def actualizar_terreno(
    payload: TerrenoUpdate,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> TerrenoOut:
    try:
        return terreno_service.actualizar_terreno(db, proyecto, payload)
    except TerrenoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
