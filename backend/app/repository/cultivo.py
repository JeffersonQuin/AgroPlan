"""Acceso al catálogo de cultivos (solo lectura)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalogo import Cultivo


def list_all(db: Session, *, solo_activos: bool = True) -> list[Cultivo]:
    stmt = select(Cultivo)
    if solo_activos:
        stmt = stmt.where(Cultivo.activo.is_(True))
    stmt = stmt.order_by(Cultivo.nombre)
    return list(db.execute(stmt).scalars().all())


def get_by_codigo(db: Session, codigo: str) -> Cultivo | None:
    return db.get(Cultivo, codigo)
