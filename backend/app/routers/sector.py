"""Endpoints de los sectores de riego."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_proyecto_actual
from app.models.proyecto import Proyecto
from app.schemas.riego import (
    DisenoOut,
    SectoresIn,
    SectorOut,
    SectorUpdate,
)
from app.services import riego as riego_service
from app.services.riego import RiegoServiceError

router = APIRouter(prefix="/proyectos", tags=["riego"])


@router.get("/{proyecto_id}/riego/sectores", response_model=list[SectorOut])
def listar_sectores(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> list[SectorOut]:
    try:
        return riego_service.listar_sectores(db, proyecto)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.put("/{proyecto_id}/riego/sectores", response_model=DisenoOut)
def aplicar_sectores(
    payload: SectoresIn,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> DisenoOut:
    try:
        return riego_service.generar(db, proyecto, payload)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get(
    "/{proyecto_id}/riego/sectores/{sector_id}", response_model=SectorOut
)
def obtener_sector(
    sector_id: uuid.UUID,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> SectorOut:
    try:
        return riego_service.obtener_sector(db, proyecto, sector_id)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.patch(
    "/{proyecto_id}/riego/sectores/{sector_id}", response_model=SectorOut
)
def actualizar_sector(
    sector_id: uuid.UUID,
    payload: SectorUpdate,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> SectorOut:
    try:
        return riego_service.actualizar_sector(
            db, proyecto, sector_id, payload
        )
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
