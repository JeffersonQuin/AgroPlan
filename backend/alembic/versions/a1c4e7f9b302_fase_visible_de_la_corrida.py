"""fase visible de la corrida del agente

La corrida del agente expone un solo ``estado`` (``corriendo``) para todo el proceso.
Con el modelo tardando casi todo el minuto y medio, la pantalla del paso 4 no tiene
nada que mostrar y el usuario cree que se colgó.

``fase`` es el paso real que el backend está ejecutando (``contexto``, ``modelo``,
``validacion``, ``precios``, ``red``, ``listo``) y ``fase_desde`` desde cuándo entró
en él, para que el cronómetro del frontend se calcule contra el servidor y recargar
la página no reinicie ni infle el conteo.

Las dos columnas son nullable: las corridas viejas no tienen fase y se siguen
devolviendo con ``None``. Migración aditiva, sin tocar filas existentes.

Revision ID: a1c4e7f9b302
Revises: c9e3f6a1d742
Create Date: 2026-11-25 09:40:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1c4e7f9b302"
down_revision: str | Sequence[str] | None = "c9e3f6a1d742"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "agente_corridas", sa.Column("fase", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "agente_corridas",
        sa.Column("fase_desde", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema: se pierden las fases, no las corridas."""
    op.drop_column("agente_corridas", "fase_desde")
    op.drop_column("agente_corridas", "fase")
