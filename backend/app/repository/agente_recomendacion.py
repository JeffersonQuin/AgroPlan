"""Acceso a las recomendaciones emitidas por una corrida del agente."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agente import AgenteRecomendacion


def list_by_corrida(
    db: Session, corrida_id: uuid.UUID
) -> list[AgenteRecomendacion]:
    stmt = (
        select(AgenteRecomendacion)
        .where(AgenteRecomendacion.corrida_id == corrida_id)
        .order_by(AgenteRecomendacion.tipo)
    )
    return list(db.execute(stmt).scalars().all())


def get_by_id(
    db: Session, recomendacion_id: uuid.UUID, corrida_id: uuid.UUID | None = None
) -> AgenteRecomendacion | None:
    stmt = select(AgenteRecomendacion).where(
        AgenteRecomendacion.id == recomendacion_id
    )
    if corrida_id is not None:
        stmt = stmt.where(AgenteRecomendacion.corrida_id == corrida_id)
    return db.execute(stmt).scalar_one_or_none()


def add(db: Session, recomendacion: AgenteRecomendacion) -> AgenteRecomendacion:
    db.add(recomendacion)
    db.commit()
    db.refresh(recomendacion)
    return recomendacion


def update(
    db: Session, recomendacion: AgenteRecomendacion
) -> AgenteRecomendacion:
    db.add(recomendacion)
    db.commit()
    db.refresh(recomendacion)
    return recomendacion
