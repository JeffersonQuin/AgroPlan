"""Documento final del paso 4, compuesto a partir de las tablas del proyecto."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_proyecto_actual
from app.models.proyecto import Proyecto
from app.schemas.agente import ResultadoProyectoOut
from app.services import agente as agente_service
from app.services.agente import AgenteServiceError

router = APIRouter(prefix="/proyectos", tags=["agente"])


@router.get("/{proyecto_id}/resultado", response_model=ResultadoProyectoOut)
def obtener_resultado(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
) -> ResultadoProyectoOut:
    try:
        return agente_service.resultado_proyecto(db, proyecto)
    except AgenteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
