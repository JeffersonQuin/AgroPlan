"""Reglas de negocio de proyectos.

El proyecto es la raíz de propiedad: todo endpoint anidado valida que el proyecto
exista, no esté eliminado y pertenezca al usuario autenticado.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.enums import EstadoProyecto
from app.models.proyecto import Proyecto
from app.models.usuario import Usuario
from app.repository import proyecto as proyecto_repo
from app.repository import proyecto_cultivo as proyecto_cultivo_repo
from app.repository import sistema_riego as sistema_riego_repo
from app.repository import terreno as terreno_repo
from app.schemas.proyecto import (
    ProyectoCreate,
    ProyectoListadoOut,
    ProyectoOut,
    ProyectoUpdate,
)


class ProyectoServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def get_proyecto(db: Session, proyecto_id: uuid.UUID, usuario: Usuario) -> Proyecto:
    proyecto = proyecto_repo.get_by_id(db, proyecto_id, usuario.id)
    if proyecto is None:
        raise ProyectoServiceError(404, "Proyecto no encontrado")
    return proyecto


def listar_proyectos(
    db: Session, usuario: Usuario, skip: int = 0, limit: int = 100
) -> list[ProyectoListadoOut]:
    proyectos = proyecto_repo.list_by_usuario(db, usuario.id, skip=skip, limit=limit)
    salida: list[ProyectoListadoOut] = []
    for proyecto in proyectos:
        terreno = terreno_repo.get_by_proyecto(db, proyecto.id)
        sistema = sistema_riego_repo.get_by_proyecto(db, proyecto.id)
        salida.append(
            ProyectoListadoOut(
                id=proyecto.id,
                nombre=proyecto.nombre,
                zona=proyecto.zona,
                unidad=proyecto.unidad,
                estado=proyecto.estado,
                area_m2=float(terreno.area_m2) if terreno is not None else None,
                cultivos_count=proyecto_cultivo_repo.count_by_proyecto(
                    db, proyecto.id
                ),
                sistema_tipo=sistema.tipo if sistema is not None else None,
                ultimo_paso_completado=proyecto.ultimo_paso_completado,
                actualizado_en=proyecto.actualizado_en,
                version=proyecto.version,
            )
        )
    return salida


def crear_proyecto(db: Session, usuario: Usuario, data: ProyectoCreate) -> ProyectoOut:
    nombre = data.nombre.strip()
    if not nombre:
        raise ProyectoServiceError(422, "El nombre del proyecto no puede estar vacío")

    proyecto = Proyecto(
        usuario_id=usuario.id,
        nombre=nombre,
        zona=data.zona.strip() if data.zona else None,
        unidad=data.unidad.value,
        estado=EstadoProyecto.BORRADOR.value,
        paso_actual=1,
        ultimo_paso_completado=0,
        version=1,
    )
    proyecto = proyecto_repo.create(db, proyecto)
    return ProyectoOut.model_validate(proyecto)


def obtener_proyecto(
    db: Session, proyecto_id: uuid.UUID, usuario: Usuario
) -> ProyectoOut:
    return ProyectoOut.model_validate(get_proyecto(db, proyecto_id, usuario))


def actualizar_proyecto(
    db: Session, proyecto_id: uuid.UUID, data: ProyectoUpdate, usuario: Usuario
) -> ProyectoOut:
    proyecto = get_proyecto(db, proyecto_id, usuario)
    if data.version != proyecto.version:
        raise ProyectoServiceError(
            409,
            "El proyecto fue modificado por otra sesión. Recarga e intenta de nuevo.",
        )

    campos = data.model_fields_set
    if "nombre" in campos and data.nombre is not None:
        nombre = data.nombre.strip()
        if not nombre:
            raise ProyectoServiceError(
                422, "El nombre del proyecto no puede estar vacío"
            )
        proyecto.nombre = nombre
    if "zona" in campos:
        proyecto.zona = data.zona.strip() if data.zona else None
    if "unidad" in campos and data.unidad is not None:
        proyecto.unidad = data.unidad.value
    if "paso_actual" in campos and data.paso_actual is not None:
        proyecto.paso_actual = data.paso_actual
    if "ultimo_paso_completado" in campos and data.ultimo_paso_completado is not None:
        proyecto.ultimo_paso_completado = data.ultimo_paso_completado

    if proyecto.ultimo_paso_completado >= 4:
        proyecto.estado = EstadoProyecto.COMPLETADO.value
    elif proyecto.ultimo_paso_completado > 0:
        proyecto.estado = EstadoProyecto.EN_PROGRESO.value
    else:
        proyecto.estado = EstadoProyecto.BORRADOR.value

    proyecto.version += 1
    proyecto = proyecto_repo.update(db, proyecto)
    return ProyectoOut.model_validate(proyecto)


def eliminar_proyecto(db: Session, proyecto_id: uuid.UUID, usuario: Usuario) -> None:
    proyecto = get_proyecto(db, proyecto_id, usuario)
    proyecto_repo.soft_delete(db, proyecto, datetime.now(timezone.utc))
