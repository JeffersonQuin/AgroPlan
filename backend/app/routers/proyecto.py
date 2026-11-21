"""Endpoints de proyectos: listado, alta, consulta, autosave y baja lógica."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_proyecto_actual
from app.models.proyecto import Proyecto
from app.models.usuario import Usuario
from app.schemas.proyecto import (
    ProyectoCreate,
    ProyectoListadoOut,
    ProyectoOut,
    ProyectoUpdate,
)
from app.services import proyecto as proyecto_service
from app.services.proyecto import ProyectoServiceError

router = APIRouter(prefix="/proyectos", tags=["proyectos"])


@router.get("", response_model=list[ProyectoListadoOut])
def listar_proyectos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> list[ProyectoListadoOut]:
    return proyecto_service.listar_proyectos(
        db, current_user, skip=skip, limit=limit
    )


@router.post("", response_model=ProyectoOut, status_code=status.HTTP_201_CREATED)
def crear_proyecto(
    payload: ProyectoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ProyectoOut:
    return proyecto_service.crear_proyecto(db, current_user, payload)


@router.get("/{proyecto_id}", response_model=ProyectoOut)
def obtener_proyecto(
    proyecto: Proyecto = Depends(get_proyecto_actual),
) -> ProyectoOut:
    return ProyectoOut.model_validate(proyecto)


@router.patch("/{proyecto_id}", response_model=ProyectoOut)
def actualizar_proyecto(
    payload: ProyectoUpdate,
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ProyectoOut:
    try:
        return proyecto_service.actualizar_proyecto(
            db, proyecto.id, payload, current_user
        )
    except ProyectoServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.delete("/{proyecto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_proyecto(
    proyecto: Proyecto = Depends(get_proyecto_actual),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> None:
    proyecto_service.eliminar_proyecto(db, proyecto.id, current_user)
