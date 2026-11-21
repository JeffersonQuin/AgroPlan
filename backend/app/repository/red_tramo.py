"""Acceso a los tramos de tubería de la red de riego."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.riego import RedTramo


def list_by_sistema(db: Session, sistema_id: uuid.UUID) -> list[RedTramo]:
    stmt = (
        select(RedTramo)
        .where(RedTramo.sistema_id == sistema_id)
        .order_by(RedTramo.tipo, RedTramo.orden)
    )
    return list(db.execute(stmt).scalars().all())


def get_by_id(
    db: Session, tramo_id: uuid.UUID, sistema_id: uuid.UUID | None = None
) -> RedTramo | None:
    stmt = select(RedTramo).where(RedTramo.id == tramo_id)
    if sistema_id is not None:
        stmt = stmt.where(RedTramo.sistema_id == sistema_id)
    return db.execute(stmt).scalar_one_or_none()


def add(db: Session, tramo: RedTramo) -> RedTramo:
    db.add(tramo)
    db.flush()
    return tramo


def delete_by_sistema(db: Session, sistema_id: uuid.UUID) -> None:
    db.execute(delete(RedTramo).where(RedTramo.sistema_id == sistema_id))
