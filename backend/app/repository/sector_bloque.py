"""Acceso al reparto de bloques de cultivo entre sectores de riego."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.riego import SectorBloque


def list_by_sector(db: Session, sector_id: uuid.UUID) -> list[SectorBloque]:
    stmt = (
        select(SectorBloque)
        .where(SectorBloque.sector_id == sector_id)
        .order_by(SectorBloque.id)
    )
    return list(db.execute(stmt).scalars().all())


def get_by_id(
    db: Session, vinculo_id: uuid.UUID, sector_id: uuid.UUID | None = None
) -> SectorBloque | None:
    stmt = select(SectorBloque).where(SectorBloque.id == vinculo_id)
    if sector_id is not None:
        stmt = stmt.where(SectorBloque.sector_id == sector_id)
    return db.execute(stmt).scalar_one_or_none()


def get_by_sector_and_bloque(
    db: Session, sector_id: uuid.UUID, bloque_id: uuid.UUID
) -> SectorBloque | None:
    stmt = select(SectorBloque).where(
        SectorBloque.sector_id == sector_id,
        SectorBloque.proyecto_cultivo_id == bloque_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def add(db: Session, vinculo: SectorBloque) -> SectorBloque:
    db.add(vinculo)
    db.flush()
    return vinculo


def delete(db: Session, vinculo: SectorBloque) -> None:
    db.delete(vinculo)
    db.commit()


def delete_by_sector_ids(db: Session, sector_ids: list[uuid.UUID]) -> None:
    if not sector_ids:
        return
    db.execute(
        sa_delete(SectorBloque).where(SectorBloque.sector_id.in_(sector_ids))
    )


def delete_by_proyecto_cultivo(db: Session, bloque_id: uuid.UUID) -> None:
    db.execute(
        sa_delete(SectorBloque).where(
            SectorBloque.proyecto_cultivo_id == bloque_id
        )
    )


def sum_area_by_sector(db: Session, sector_id: uuid.UUID) -> Decimal:
    stmt = select(func.coalesce(func.sum(SectorBloque.area_m2), 0)).where(
        SectorBloque.sector_id == sector_id
    )
    return Decimal(str(db.execute(stmt).scalar_one()))
