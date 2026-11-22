"""Acceso al terreno de un proyecto (relación uno a uno)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.proyecto import Terreno


def get_by_proyecto(db: Session, proyecto_id: uuid.UUID) -> Terreno | None:
    stmt = select(Terreno).where(Terreno.proyecto_id == proyecto_id)
    return db.execute(stmt).scalar_one_or_none()


def create(db: Session, terreno: Terreno) -> Terreno:
    db.add(terreno)
    db.commit()
    db.refresh(terreno)
    return terreno


def update(db: Session, terreno: Terreno) -> Terreno:
    db.add(terreno)
    db.commit()
    db.refresh(terreno)
    return terreno
