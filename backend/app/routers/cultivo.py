"""Catálogo de cultivos (solo lectura)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.repository import cultivo as cultivo_repo
from app.schemas.catalogo import CultivoOut

router = APIRouter(prefix="/catalogos/cultivos", tags=["catalogos"])


@router.get("", response_model=list[CultivoOut])
def listar_cultivos(db: Session = Depends(get_db)) -> list[CultivoOut]:
    return [
        CultivoOut.model_validate(cultivo)
        for cultivo in cultivo_repo.list_all(db)
    ]


@router.get("/{codigo}", response_model=CultivoOut)
def obtener_cultivo(
    codigo: str, db: Session = Depends(get_db)
) -> CultivoOut:
    cultivo = cultivo_repo.get_by_codigo(db, codigo)
    if cultivo is None:
        raise HTTPException(status_code=404, detail="Cultivo no encontrado")
    return CultivoOut.model_validate(cultivo)
