"""Catálogo de suelos (solo lectura)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.repository import suelo as suelo_repo
from app.schemas.catalogo import SueloOut

router = APIRouter(prefix="/catalogos/suelos", tags=["catalogos"])


@router.get("", response_model=list[SueloOut])
def listar_suelos(db: Session = Depends(get_db)) -> list[SueloOut]:
    return [
        SueloOut.model_validate(suelo) for suelo in suelo_repo.list_all(db)
    ]


@router.get("/{codigo}", response_model=SueloOut)
def obtener_suelo(codigo: str, db: Session = Depends(get_db)) -> SueloOut:
    suelo = suelo_repo.get_by_codigo(db, codigo)
    if suelo is None:
        raise HTTPException(status_code=404, detail="Suelo no encontrado")
    return SueloOut.model_validate(suelo)
