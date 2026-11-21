"""Endpoints de los nodos de la red de riego."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_proyecto_actual
from app.models.proyecto import Proyecto
from app.schemas.riego import NodoOut
from app.services import riego as riego_service
from app.services.riego import RiegoServiceError

router = APIRouter(prefix="/proyectos", tags=["riego"])


@router.get("/{proyecto_id}/riego/nodos", response_model=list[NodoOut])
def listar_nodos(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> list[NodoOut]:
    try:
        return riego_service.listar_nodos(db, proyecto)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get(
    "/{proyecto_id}/riego/nodos/{nodo_id}", response_model=NodoOut
)
def obtener_nodo(
    nodo_id: uuid.UUID,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> NodoOut:
    try:
        return riego_service.obtener_nodo(db, proyecto, nodo_id)
    except RiegoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
