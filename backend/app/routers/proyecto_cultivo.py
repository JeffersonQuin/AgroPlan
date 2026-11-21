"""Endpoints de los bloques de cultivo y del balance de superficie."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_proyecto_actual
from app.models.proyecto import Proyecto
from app.schemas.cultivo import (
    BalanceArea,
    BloqueCultivoCreate,
    BloqueCultivoOut,
    BloqueCultivoUpdate,
    CultivoRespuesta,
)
from app.services import cultivo as cultivo_service
from app.services.cultivo import CultivoServiceError

router = APIRouter(prefix="/proyectos", tags=["proyecto_cultivo"])


@router.get("/{proyecto_id}/cultivos", response_model=list[BloqueCultivoOut])
def listar_cultivos(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> list[BloqueCultivoOut]:
    return cultivo_service.listar_bloques(db, proyecto)


@router.post(
    "/{proyecto_id}/cultivos",
    response_model=CultivoRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def crear_cultivo(
    payload: BloqueCultivoCreate,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> CultivoRespuesta:
    try:
        return cultivo_service.crear_bloque(db, proyecto, payload)
    except CultivoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{proyecto_id}/cultivos/balance", response_model=BalanceArea)
def obtener_balance(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> BalanceArea:
    try:
        return cultivo_service.balance(db, proyecto)
    except CultivoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{proyecto_id}/cultivos/{bloque_id}", response_model=BloqueCultivoOut)
def obtener_cultivo(
    bloque_id: uuid.UUID,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> BloqueCultivoOut:
    try:
        return cultivo_service.obtener_bloque(db, proyecto, bloque_id)
    except CultivoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.patch("/{proyecto_id}/cultivos/{bloque_id}", response_model=CultivoRespuesta)
def actualizar_cultivo(
    bloque_id: uuid.UUID,
    payload: BloqueCultivoUpdate,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> CultivoRespuesta:
    try:
        return cultivo_service.actualizar_bloque(db, proyecto, bloque_id, payload)
    except CultivoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.delete(
    "/{proyecto_id}/cultivos/{bloque_id}", status_code=status.HTTP_204_NO_CONTENT
)
def eliminar_cultivo(
    bloque_id: uuid.UUID,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> None:
    try:
        cultivo_service.eliminar_bloque(db, proyecto, bloque_id)
    except CultivoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
