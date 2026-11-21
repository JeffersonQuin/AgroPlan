"""marcar el origen de las fichas de cultivo

El agente puede investigar un producto que no existe en el catálogo y darle de alta
con la ficha que encontró (alta automática con aviso). Para que eso sea auditable, la
tabla `cultivos` necesita distinguir esas filas de las sembradas a mano, guardar de
dónde salió la información y saber si alguien ya la revisó.

`origen` arranca en 'humano' para todas las filas existentes: nada de lo que ya está
sembrado cambia de significado.

Revision ID: c4e9a1b73f21
Revises: 736aa2b57e30
Create Date: 2026-11-21 22:41:03.118472

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c4e9a1b73f21"
down_revision: str | Sequence[str] | None = "736aa2b57e30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "cultivos",
        sa.Column(
            "origen", sa.String(length=10), nullable=False, server_default="humano"
        ),
    )
    op.add_column(
        "cultivos",
        sa.Column("revisado_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cultivos",
        sa.Column(
            "fuentes",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
    )
    with op.batch_alter_table("cultivos") as batch:
        batch.create_check_constraint(
            "ck_cultivos_origen", "origen IN ('humano', 'agente')"
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("cultivos") as batch:
        batch.drop_constraint("ck_cultivos_origen", type_="check")
    op.drop_column("cultivos", "fuentes")
    op.drop_column("cultivos", "revisado_en")
    op.drop_column("cultivos", "origen")
