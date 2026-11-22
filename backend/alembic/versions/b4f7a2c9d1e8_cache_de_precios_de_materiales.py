"""caché de precios de materiales del agente

El agente investiga precios con fuentes web para el cómputo del paso 4 y el sistema
los guardaba sólo dentro de la salida congelada de la corrida: cada proyecto de cada
usuario volvía a investigar lo mismo. Esta tabla guarda un precio por material —no
por corrida— para reutilizarlo mientras siga vigente.

``clave`` es la identidad normalizada (rubro + descripción + unidad) y es única: el
upsert actualiza la misma fila cuando el precio se vuelve a investigar.
``recuperado_en`` es cuándo se obtuvo el precio (define la vigencia) y
``actualizado_en`` cuándo se escribió por última vez.

Es una tabla nueva y sin datos previos: no toca ninguna fila existente.

Revision ID: b4f7a2c9d1e8
Revises: a3d8e6b0c571
Create Date: 2026-11-23 10:12:44.318702

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b4f7a2c9d1e8"
down_revision: str | Sequence[str] | None = "a3d8e6b0c571"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "materiales_precio",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clave", sa.String(length=300), nullable=False),
        sa.Column("rubro", sa.String(length=60), nullable=False),
        sa.Column("descripcion", sa.String(length=200), nullable=False),
        sa.Column("unidad", sa.String(length=20), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("precio_unitario_bs", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("fuente_url", sa.Text(), nullable=True),
        sa.Column(
            "recuperado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "precio_unitario_bs > 0", name="ck_materiales_precio_positivo"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clave"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("materiales_precio")
