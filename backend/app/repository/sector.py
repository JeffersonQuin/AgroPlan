"""Acceso a los sectores de riego de un sistema."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.riego import Sector


def list_by_sistema(db: Session, sistema_id: uuid.UUID) -> list[Sector]:
    stmt = (
        select(Sector)
        .where(Sector.sistema_id == sistema_id)
        .options(selectinload(Sector.bloques))
        .order_by(Sector.numero)
    )
    return list(db.execute(stmt).scalars().all())


def list_ids_by_sistema(db: Session, sistema_id: uuid.UUID) -> list[uuid.UUID]:
    stmt = select(Sector.id).where(Sector.sistema_id == sistema_id)
    return list(db.execute(stmt).scalars().all())


def get_by_id(
    db: Session, sector_id: uuid.UUID, sistema_id: uuid.UUID | None = None
) -> Sector | None:
    stmt = (
        select(Sector)
        .where(Sector.id == sector_id)
        .options(selectinload(Sector.bloques))
    )
    if sistema_id is not None:
        stmt = stmt.where(Sector.sistema_id == sistema_id)
    return db.execute(stmt).scalar_one_or_none()


def add(db: Session, sector: Sector) -> Sector:
    db.add(sector)
    db.flush()
    return sector


def update(db: Session, sector: Sector) -> Sector:
    db.add(sector)
    db.commit()
    db.refresh(sector)
    return sector


def delete_by_sistema(db: Session, sistema_id: uuid.UUID) -> None:
    db.execute(delete(Sector).where(Sector.sistema_id == sistema_id))
