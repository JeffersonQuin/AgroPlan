"""Acceso a las corridas del agente de recomendaciones."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agente import AgenteCorrida


def create(db: Session, corrida: AgenteCorrida) -> AgenteCorrida:
    db.add(corrida)
    db.commit()
    db.refresh(corrida)
    return corrida


def get_by_id(
    db: Session, corrida_id: uuid.UUID, proyecto_id: uuid.UUID | None = None
) -> AgenteCorrida | None:
    stmt = select(AgenteCorrida).where(AgenteCorrida.id == corrida_id)
    if proyecto_id is not None:
        stmt = stmt.where(AgenteCorrida.proyecto_id == proyecto_id)
    return db.execute(stmt).scalar_one_or_none()


def list_by_proyecto(db: Session, proyecto_id: uuid.UUID) -> list[AgenteCorrida]:
    stmt = (
        select(AgenteCorrida)
        .where(AgenteCorrida.proyecto_id == proyecto_id)
        .order_by(AgenteCorrida.iniciado_en.desc())
    )
    return list(db.execute(stmt).scalars().all())


def update(db: Session, corrida: AgenteCorrida) -> AgenteCorrida:
    db.add(corrida)
    db.commit()
    db.refresh(corrida)
    return corrida
