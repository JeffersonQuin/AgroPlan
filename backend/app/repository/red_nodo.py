"""Acceso a los nodos puntuales de la red de riego."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.riego import RedNodo


def list_by_sistema(db: Session, sistema_id: uuid.UUID) -> list[RedNodo]:
    stmt = (
        select(RedNodo)
        .where(RedNodo.sistema_id == sistema_id)
        .order_by(RedNodo.tipo)
    )
    return list(db.execute(stmt).scalars().all())


def get_by_id(
    db: Session, nodo_id: uuid.UUID, sistema_id: uuid.UUID | None = None
) -> RedNodo | None:
    stmt = select(RedNodo).where(RedNodo.id == nodo_id)
    if sistema_id is not None:
        stmt = stmt.where(RedNodo.sistema_id == sistema_id)
    return db.execute(stmt).scalar_one_or_none()


def add(db: Session, nodo: RedNodo) -> RedNodo:
    db.add(nodo)
    db.flush()
    return nodo


def delete_by_sistema(db: Session, sistema_id: uuid.UUID) -> None:
    db.execute(delete(RedNodo).where(RedNodo.sistema_id == sistema_id))
