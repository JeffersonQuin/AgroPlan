"""kc, aptitud de suelo y nivel dinámico para el paso 2

El prototipo del paso 2 muestra el Kc pico del cultivo y necesita saber si el suelo
del terreno le sirve; el paso 1 pide la profundidad del nivel dinámico. Nada de eso
existía en la base.

`aptitud_suelo` guarda un veredicto por código de suelo:
``{"franco": {"veredicto": "apto", "motivo": "..."}}``. Un suelo ausente del mapa
significa "no sabemos", y el sistema no inventa: no emite veredicto.

Todo es aditivo y nullable: ninguna fila existente cambia de significado.

Revision ID: d7a1e4c9b2f0
Revises: c4e9a1b73f21
Create Date: 2026-11-21 23:58:12.402915

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d7a1e4c9b2f0"
down_revision: str | Sequence[str] | None = "c4e9a1b73f21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("cultivos", sa.Column("kc", sa.Numeric(precision=4, scale=2), nullable=True))
    op.add_column("cultivos", sa.Column("aptitud_suelo", JSONB, nullable=True))
    op.add_column(
        "terrenos",
        sa.Column(
            "profundidad_nivel_dinamico_m",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("terrenos", "profundidad_nivel_dinamico_m")
    op.drop_column("cultivos", "aptitud_suelo")
    op.drop_column("cultivos", "kc")
