"""imagen de la ficha curada en el catálogo de cultivos

El informe del paso 4 muestra imágenes híbridas (S4): primero la ficha curada, y sólo
si falta, la que investiga el agente. Hasta ahora la imagen vivía únicamente en la
ficha curada del repo, así que el catálogo no la podía exponer ni el agente sabía que
ya existía.

Esta migración es aditiva: agrega tres columnas nullable y copia a cada fila la
imagen, su fuente y su crédito desde la ficha curada cuando los tenga. Si una base ya
la corrió cuando las fichas todavía tenían las URLs en ``null``, la revisión de datos
siguiente vuelve a sincronizarlas: no hace falta recrear esta migración.

Ojo con revertirla: el `downgrade` borra `imagen_url`, `imagen_fuente_url` e
`imagen_credito` y con ellas las URLs sembradas. Se pueden volver a copiar desde las
fichas con un `upgrade`.

Revision ID: f5a2c8d9e310
Revises: b4f7a2c9d1e8
Create Date: 2026-11-24 09:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f5a2c8d9e310"
down_revision: str | Sequence[str] | None = "b4f7a2c9d1e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _imagenes_curadas() -> dict[str, tuple[str, str | None, str | None]]:
    """Imagen, fuente y crédito de las fichas curadas que ya la tengan.

    Se leen del mismo cargador que usa la API: si mañana una ficha suma su URL, el
    backfill no necesita una migración nueva para las filas que se creen después, y
    una ficha inválida se descarta con su warning en vez de romper el upgrade.
    """

    from app.agente import fichas

    imagenes: dict[str, tuple[str, str | None, str | None]] = {}
    for ficha in fichas.listar():
        if ficha.imagen:
            imagenes[ficha.codigo] = (
                ficha.imagen,
                ficha.imagen_fuente,
                ficha.imagen_credito,
            )
    return imagenes


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "cultivos", sa.Column("imagen_url", sa.String(length=1000), nullable=True)
    )
    op.add_column(
        "cultivos",
        sa.Column("imagen_fuente_url", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "cultivos", sa.Column("imagen_credito", sa.String(length=500), nullable=True)
    )

    for codigo, (imagen, imagen_fuente, imagen_credito) in (
        _imagenes_curadas().items()
    ):
        op.execute(
            sa.text(
                "UPDATE cultivos SET imagen_url = :imagen, "
                "imagen_fuente_url = :imagen_fuente, "
                "imagen_credito = :imagen_credito WHERE codigo = :codigo"
            ).bindparams(
                imagen=imagen,
                imagen_fuente=imagen_fuente,
                imagen_credito=imagen_credito,
                codigo=codigo,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("cultivos", "imagen_credito")
    op.drop_column("cultivos", "imagen_fuente_url")
    op.drop_column("cultivos", "imagen_url")
