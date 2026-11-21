"""Endpoints del reparto de bloques de cultivo entre sectores."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_proyecto_actual
from app.models.proyecto import Proyecto
from app.schemas.riego import SectorBloqueIn, SectorBloqueOut
from app.services import riego as riego_service
from app.services.riego import RiegoServiceError

router = APIRouter(prefix="/proyectos", tags=["riego"])


@router.get(
    "/{proyecto_id}/riego/sectores/{sector_id}/bloques",
    response_model=list[SectorBloqueOut],
)
def listar_sector_bloques(
    sector_id: uuid.UUID,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> list[SectorBloqueOut]:
    try:
        return riego_service.listar_sector_bloques(db, proyecto, sector_id)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post(
    "/{proyecto_id}/riego/sectores/{sector_id}/bloques",
    response_model=SectorBloqueOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_sector_bloque(
    sector_id: uuid.UUID,
    payload: SectorBloqueIn,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> SectorBloqueOut:
    try:
        return riego_service.crear_sector_bloque(
            db, proyecto, sector_id, payload
        )
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get(
    "/{proyecto_id}/riego/sectores/{sector_id}/bloques/{vinculo_id}",
    response_model=SectorBloqueOut,
)
def obtener_sector_bloque(
    sector_id: uuid.UUID,
    vinculo_id: uuid.UUID,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> SectorBloqueOut:
    try:
        return riego_service.obtener_sector_bloque(
            db, proyecto, sector_id, vinculo_id
        )
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.delete(
    "/{proyecto_id}/riego/sectores/{sector_id}/bloques/{vinculo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_sector_bloque(
    sector_id: uuid.UUID,
    vinculo_id: uuid.UUID,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> None:
    try:
        riego_service.eliminar_sector_bloque(
            db, proyecto, sector_id, vinculo_id
        )
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
