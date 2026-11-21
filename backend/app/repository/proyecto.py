"""Acceso a proyectos. Todas las consultas respetan el borrado lógico."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.proyecto import Proyecto


def get_by_id(
    db: Session,
    proyecto_id: uuid.UUID,
    usuario_id: int | None = None,
    *,
    incluir_eliminados: bool = False,
) -> Proyecto | None:
    stmt = select(Proyecto).where(Proyecto.id == proyecto_id)
    if usuario_id is not None:
        stmt = stmt.where(Proyecto.usuario_id == usuario_id)
    if not incluir_eliminados:
        stmt = stmt.where(Proyecto.eliminado_en.is_(None))
    return db.execute(stmt).scalar_one_or_none()


def list_by_usuario(
    db: Session, usuario_id: int, skip: int = 0, limit: int = 100
) -> list[Proyecto]:
    stmt = (
        select(Proyecto)
        .where(Proyecto.usuario_id == usuario_id, Proyecto.eliminado_en.is_(None))
        .order_by(Proyecto.actualizado_en.desc(), Proyecto.creado_en.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def create(db: Session, proyecto: Proyecto) -> Proyecto:
    db.add(proyecto)
    db.commit()
    db.refresh(proyecto)
    return proyecto


def update(db: Session, proyecto: Proyecto) -> Proyecto:
    db.add(proyecto)
    db.commit()
    db.refresh(proyecto)
    return proyecto


def soft_delete(db: Session, proyecto: Proyecto, eliminado_en) -> Proyecto:
    proyecto.eliminado_en = eliminado_en
    return update(db, proyecto)
