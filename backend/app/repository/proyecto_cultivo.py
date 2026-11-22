"""Acceso a los bloques de cultivo de un proyecto."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.proyecto_cultivo import ProyectoCultivo


def list_by_proyecto(db: Session, proyecto_id: uuid.UUID) -> list[ProyectoCultivo]:
    stmt = (
        select(ProyectoCultivo)
        .where(ProyectoCultivo.proyecto_id == proyecto_id)
        .order_by(ProyectoCultivo.orden, ProyectoCultivo.creado_en)
    )
    return list(db.execute(stmt).scalars().all())


def get_by_id(
    db: Session, bloque_id: uuid.UUID, proyecto_id: uuid.UUID | None = None
) -> ProyectoCultivo | None:
    stmt = select(ProyectoCultivo).where(ProyectoCultivo.id == bloque_id)
    if proyecto_id is not None:
        stmt = stmt.where(ProyectoCultivo.proyecto_id == proyecto_id)
    return db.execute(stmt).scalar_one_or_none()


def next_orden(db: Session, proyecto_id: uuid.UUID) -> int:
    stmt = select(func.max(ProyectoCultivo.orden)).where(
        ProyectoCultivo.proyecto_id == proyecto_id
    )
    actual = db.execute(stmt).scalar_one_or_none()
    return int(actual or 0) + 1


def count_by_proyecto(db: Session, proyecto_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(ProyectoCultivo).where(
        ProyectoCultivo.proyecto_id == proyecto_id
    )
    return int(db.execute(stmt).scalar_one())


def sum_area(db: Session, proyecto_id: uuid.UUID) -> Decimal:
    stmt = select(func.coalesce(func.sum(ProyectoCultivo.area_m2), 0)).where(
        ProyectoCultivo.proyecto_id == proyecto_id
    )
    return Decimal(str(db.execute(stmt).scalar_one()))


def create(db: Session, bloque: ProyectoCultivo) -> ProyectoCultivo:
    db.add(bloque)
    db.commit()
    db.refresh(bloque)
    return bloque


def update(db: Session, bloque: ProyectoCultivo) -> ProyectoCultivo:
    db.add(bloque)
    db.commit()
    db.refresh(bloque)
    return bloque


def delete(db: Session, bloque: ProyectoCultivo) -> None:
    db.delete(bloque)
    db.commit()
