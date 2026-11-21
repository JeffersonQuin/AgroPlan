"""Acceso a las fuentes citadas por una corrida del agente."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agente import AgenteFuente


def list_by_corrida(db: Session, corrida_id: uuid.UUID) -> list[AgenteFuente]:
    stmt = (
        select(AgenteFuente)
        .where(AgenteFuente.corrida_id == corrida_id)
        .order_by(AgenteFuente.recuperado_en)
    )
    return list(db.execute(stmt).scalars().all())


def add(db: Session, fuente: AgenteFuente) -> AgenteFuente:
    db.add(fuente)
    db.commit()
    db.refresh(fuente)
    return fuente
