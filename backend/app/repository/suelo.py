"""Acceso al catálogo de suelos (solo lectura)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalogo import Suelo


def list_all(db: Session) -> list[Suelo]:
    stmt = select(Suelo).order_by(Suelo.nombre)
    return list(db.execute(stmt).scalars().all())


def get_by_codigo(db: Session, codigo: str) -> Suelo | None:
    return db.get(Suelo, codigo)
