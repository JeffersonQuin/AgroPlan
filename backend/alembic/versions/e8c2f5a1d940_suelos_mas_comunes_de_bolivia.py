"""suelos más comunes de Bolivia

El catálogo tenía los cuatro suelos de la textura básica (franco, arenoso, arcilloso,
limoso). Para el paso 1 faltaban los que aparecen en las zonas productivas del país:
franco arenoso y franco arcilloso de los valles, suelos salinos y calcáreos del
Altiplano, pedregosos de ladera y francos con materia orgánica de Yungas y Amazonía.

Los valores de infiltración y retención son de arranque, para que el cálculo del paso 4
sea creíble; el equipo agronómico los ajusta con una migración de datos, no en el código.

Revision ID: e8c2f5a1d940
Revises: d7a1e4c9b2f0
Create Date: 2026-11-22 00:45:10.774213

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e8c2f5a1d940"
down_revision: str | Sequence[str] | None = "d7a1e4c9b2f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# codigo, nombre, infiltracion mm/h, retencion mm/m
SUELOS_BOLIVIA: tuple[tuple[str, str, float, float], ...] = (
    ("franco_arenoso", "Franco arenoso", 18.0, 110.0),
    ("franco_arcilloso", "Franco arcilloso", 7.0, 190.0),
    ("salino", "Salino / sódico (Altiplano)", 4.0, 120.0),
    ("calcareo", "Calcáreo (Altiplano)", 9.0, 130.0),
    ("pedregoso", "Pedregoso / gravoso (laderas)", 35.0, 60.0),
    ("organico", "Franco con materia orgánica (Yungas y Amazonía)", 15.0, 210.0),
)

suelos = sa.table(
    "suelos",
    sa.column("codigo", sa.String),
    sa.column("nombre", sa.String),
    sa.column("infiltracion_mm_h", sa.Numeric),
    sa.column("retencion_agua_mm_m", sa.Numeric),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(
        suelos,
        [
            {
                "codigo": codigo,
                "nombre": nombre,
                "infiltracion_mm_h": infiltracion,
                "retencion_agua_mm_m": retencion,
            }
            for codigo, nombre, infiltracion, retencion in SUELOS_BOLIVIA
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    codigos = ", ".join(f"'{codigo}'" for codigo, *_ in SUELOS_BOLIVIA)
    op.execute(sa.text(f"DELETE FROM suelos WHERE codigo IN ({codigos})"))
