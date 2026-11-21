"""Acceso a la configuración del sistema de riego. Uno por proyecto."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.riego import SistemaRiego


def get_by_proyecto(db: Session, proyecto_id: uuid.UUID) -> SistemaRiego | None:
    stmt = select(SistemaRiego).where(SistemaRiego.proyecto_id == proyecto_id)
    return db.execute(stmt).scalar_one_or_none()


def create(db: Session, sistema: SistemaRiego) -> SistemaRiego:
    db.add(sistema)
    db.commit()
    db.refresh(sistema)
    return sistema


def update(db: Session, sistema: SistemaRiego) -> SistemaRiego:
    db.add(sistema)
    db.commit()
    db.refresh(sistema)
    return sistema


def delete(db: Session, sistema: SistemaRiego) -> None:
    db.delete(sistema)
    db.commit()
