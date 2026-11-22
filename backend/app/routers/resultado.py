"""Documento final del paso 4, compuesto a partir de las tablas del proyecto."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_proyecto_actual
from app.models.proyecto import Proyecto
from app.schemas.agente import InformePdfIn, ResultadoProyectoOut
from app.services import agente as agente_service
from app.services import informe_pdf
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


@router.post("/{proyecto_id}/pdf")
def descargar_informe(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
    data: InformePdfIn | None = None,
) -> Response:
    """Informe descargable del paso 4, generado en el backend (S8)."""

    try:
        contenido, slug = informe_pdf.informe_proyecto(
            db, proyecto, incluir=data.incluir if data is not None else None
        )
    except AgenteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="informe-{slug}.pdf"'
        },
    )
