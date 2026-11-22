"""re-sincronizar las imágenes de las fichas curadas al catálogo

La revisión f5a2c8d9e310 agregó `imagen_url`, `imagen_fuente_url` e `imagen_credito` y
copió a cada fila lo que la ficha curada tenía en ese momento. Las fichas todavía
estaban vacías, así que las bases que ya la corrieron quedaron con las tres columnas
en ``null`` aunque hoy los JSON del repo sí traen la foto y su atribución.

Esta migración de datos vuelve a leer las fichas por ``codigo`` y actualiza las tres
columnas. Es idempotente: un `UPDATE` por código sobre filas existentes, sin inserts,
así que correrla dos veces deja el mismo resultado y no duplica nada. Un código que no
existe en el catálogo simplemente no afecta filas.

El `downgrade` es un no-op: no se puede distinguir qué filas tenían la imagen antes de
esta sincronización y borrarlas perdería datos buenos. Las columnas las quita
f5a2c8d9e310.

Revision ID: c9e3f6a1d742
Revises: f5a2c8d9e310
Create Date: 2026-11-24 11:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c9e3f6a1d742"
down_revision: str | Sequence[str] | None = "f5a2c8d9e310"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _imagenes_curadas() -> dict[str, tuple[str, str | None, str | None]]:
    """Imagen, fuente y crédito de las fichas curadas que ya la tengan."""

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
    """Upgrade data."""
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
    """Downgrade data: no-op, no se puede revertir sin perder filas buenas."""
