"""Endpoints de las fuentes citadas por una corrida del agente."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_proyecto_actual
from app.models.proyecto import Proyecto
from app.schemas.agente import FuenteOut
from app.services import agente as agente_service
from app.services.agente import AgenteServiceError

router = APIRouter(prefix="/proyectos", tags=["agente"])


@router.get(
    "/{proyecto_id}/agente/corridas/{corrida_id}/fuentes",
    response_model=list[FuenteOut],
)
def listar_fuentes(
    corrida_id: uuid.UUID,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> list[FuenteOut]:
    try:
        return agente_service.listar_fuentes(db, proyecto, corrida_id)
    except AgenteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
