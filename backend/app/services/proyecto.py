"""Reglas de negocio de proyectos.

El proyecto es la raíz de propiedad: todo endpoint anidado valida que el proyecto
exista, no esté eliminado y pertenezca al usuario autenticado.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.enums import EstadoCorrida, EstadoProyecto
from app.models.proyecto import Proyecto, Terreno
from app.models.riego import SistemaRiego
from app.models.usuario import Usuario
from app.repository import agente_corrida as agente_corrida_repo
from app.repository import proyecto as proyecto_repo
from app.repository import proyecto_cultivo as proyecto_cultivo_repo
from app.repository import sistema_riego as sistema_riego_repo
from app.repository import terreno as terreno_repo
from app.schemas.proyecto import (
    GeometriaTerreno,
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
        cultivos_count = proyecto_cultivo_repo.count_by_proyecto(db, proyecto.id)
        paso = _paso_derivado(db, proyecto, terreno, sistema, cultivos_count)
        salida.append(
            ProyectoListadoOut(
                id=proyecto.id,
                nombre=proyecto.nombre,
                zona=proyecto.zona,
                unidad=proyecto.unidad,
                estado=_estado_coherente(proyecto.estado, paso),
                area_m2=float(terreno.area_m2) if terreno is not None else None,
                cultivos_count=cultivos_count,
                sistema_tipo=sistema.tipo if sistema is not None else None,
                pendiente_pct=(
                    float(terreno.pendiente_pct) if terreno is not None else None
                ),
                num_sectores=sistema.num_sectores if sistema is not None else None,
                geometria=(
                    GeometriaTerreno.model_validate(terreno.geometria)
                    if terreno is not None
                    else None
                ),
                ultimo_paso_completado=paso,
                actualizado_en=proyecto.actualizado_en,
                version=proyecto.version,
            )
        )
    return salida


def _paso_derivado(
    db: Session,
    proyecto: Proyecto,
    terreno: Terreno | None,
    sistema: SistemaRiego | None,
    cultivos_count: int,
) -> int:
    """Avance real del proyecto: terreno → cultivos → riego → corrida del agente.

    Es acumulativo y no saltea pasos: un paso superior exige los anteriores. El
    proyecto sin terreno queda en el paso 1, igual que el wizard.
    """

    paso = 1
    if terreno is not None and cultivos_count > 0:
        paso = 2
    if paso == 2 and sistema is not None:
        paso = 3
    if paso == 3 and _tiene_corrida_ok(db, proyecto):
        paso = 4
    return paso


def _tiene_corrida_ok(db: Session, proyecto: Proyecto) -> bool:
    """True si la corrida vigente terminó en ok y dejó su salida congelada."""

    if proyecto.corrida_actual_id is None:
        return False
    corrida = agente_corrida_repo.get_by_id(
        db, proyecto.corrida_actual_id, proyecto.id
    )
    if corrida is None or corrida.estado != EstadoCorrida.OK.value:
        return False
    return bool(corrida.salida)


def _estado_coherente(estado_guardado: str, paso: int) -> str:
    """``completado`` si y solo si el avance derivado llegó al paso 4.

    El resto de los estados se conserva, salvo un ``completado`` guardado a mano que el
    avance real ya no respalda: ese se degrada al estado que corresponde al paso.
    """

    if paso >= 4:
        return EstadoProyecto.COMPLETADO.value
    if estado_guardado == EstadoProyecto.COMPLETADO.value:
        return (
            EstadoProyecto.EN_PROGRESO.value
            if paso > 1
            else EstadoProyecto.BORRADOR.value
        )
    return estado_guardado


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
