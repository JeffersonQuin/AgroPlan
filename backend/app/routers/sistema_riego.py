"""Endpoints de la configuración del sistema de riego y su generación."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_proyecto_actual
from app.models.proyecto import Proyecto
from app.schemas.riego import (
    DisenoOut,
    PreviewOut,
    RedOut,
    SistemaRiegoIn,
    SistemaRiegoOut,
)
from app.services import riego as riego_service
from app.services.riego import RiegoServiceError

router = APIRouter(prefix="/proyectos", tags=["riego"])


@router.get("/{proyecto_id}/riego", response_model=SistemaRiegoOut)
def obtener_configuracion(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> SistemaRiegoOut:
    try:
        return riego_service.obtener_config(db, proyecto)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.put("/{proyecto_id}/riego", response_model=SistemaRiegoOut)
def guardar_configuracion(
    payload: SistemaRiegoIn,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> SistemaRiegoOut:
    try:
        return riego_service.upsert_config(db, proyecto, payload)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{proyecto_id}/riego/preview", response_model=PreviewOut)
def obtener_preview(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> PreviewOut:
    try:
        return riego_service.preview(db, proyecto)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/{proyecto_id}/riego/generar", response_model=DisenoOut)
def generar_diseno(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> DisenoOut:
    try:
        return riego_service.generar(db, proyecto)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{proyecto_id}/riego/diseno", response_model=DisenoOut)
def obtener_diseno(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> DisenoOut:
    try:
        return riego_service.obtener_diseno(db, proyecto)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{proyecto_id}/riego/red", response_model=RedOut)
def obtener_red(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> RedOut:
    try:
        return riego_service.obtener_red(db, proyecto)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
