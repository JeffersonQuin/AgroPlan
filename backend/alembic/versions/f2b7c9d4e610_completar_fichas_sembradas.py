"""completar las fichas sembradas con sus datos agronómicos

La migración c4e9a1b73f21 agregó `kc` y `aptitud_suelo`, y d7a1e4c9b2f0 el resto de la
ficha agronómica, pero las ocho filas sembradas del catálogo quedaron con esas columnas
vacías: el paso 2 mostraba "sin dato" para todos los cultivos que ya existían.

Esta migración copia los valores de las fichas curadas del repo (`app/agente/fichas/`)
a las filas sembradas que las tienen. Las cuatro que no tienen ficha (vid, trigo,
zanahoria, cebolla) quedan sin dato a propósito: el sistema no inventa, y se completan
agregando su ficha y una migración como ésta.

Los valores se generaron leyendo las fichas, no transcribiéndolos a mano.

Revision ID: f2b7c9d4e610
Revises: e8c2f5a1d940
Create Date: 2026-11-22 01:20:41.552301

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2b7c9d4e610"
down_revision: str | Sequence[str] | None = "e8c2f5a1d940"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# codigo, kc, plantas/m2, raiz cm, aptitud por suelo (veredicto + motivo + fuente)
FICHAS: tuple[tuple[str, float, float, int, str], ...] = (
    ("papa", 1.15, 4.0, 40, '{"franco": {"veredicto": "apto", "motivo": "Suelo equilibrado en drenaje y retención; ideal para tubérculo.", "fuente": "Ficha curada AgroPlan"}, "arenoso": {"veredicto": "condicionado", "motivo": "Drena rápido y retiene poco: regar en pulsos más frecuentes.", "fuente": "Ficha curada AgroPlan"}, "arcilloso": {"veredicto": "no_apto", "motivo": "Drenaje lento: riesgo alto de pudrición del tubérculo.", "fuente": "Ficha curada AgroPlan"}, "limoso": {"veredicto": "condicionado", "motivo": "Buena retención pero se compacta: cuidar laboreo.", "fuente": "Ficha curada AgroPlan"}}'),
    ("lechuga", 1.0, 9.0, 20, '{"franco": {"veredicto": "apto", "motivo": "Suelo ideal: humedad pareja y buen drenaje.", "fuente": "Ficha curada AgroPlan"}, "arenoso": {"veredicto": "condicionado", "motivo": "Retiene poco: aumentar frecuencia de riego.", "fuente": "Ficha curada AgroPlan"}, "arcilloso": {"veredicto": "condicionado", "motivo": "Puede encharcar: vigilar drenaje y hongos.", "fuente": "Ficha curada AgroPlan"}, "limoso": {"veredicto": "apto", "motivo": "Alta retención con buen manejo de riego.", "fuente": "Ficha curada AgroPlan"}}'),
    ("maiz", 1.2, 7.0, 80, '{"franco": {"veredicto": "apto", "motivo": "Perfil profundo y equilibrado para el sistema radical.", "fuente": "Ficha curada AgroPlan"}, "arenoso": {"veredicto": "condicionado", "motivo": "Requiere riegos más frecuentes por baja retención.", "fuente": "Ficha curada AgroPlan"}, "arcilloso": {"veredicto": "condicionado", "motivo": "Drenaje lento: riesgo de anegamiento temprano.", "fuente": "Ficha curada AgroPlan"}, "limoso": {"veredicto": "apto", "motivo": "Buena reserva de agua para el ciclo.", "fuente": "Ficha curada AgroPlan"}}'),
    ("tomate", 1.1, 2.5, 60, '{"franco": {"veredicto": "apto", "motivo": "Suelo ideal para el cultivo.", "fuente": "Ficha curada AgroPlan"}, "arenoso": {"veredicto": "condicionado", "motivo": "Riego más frecuente; sensible a estrés hídrico.", "fuente": "Ficha curada AgroPlan"}, "arcilloso": {"veredicto": "no_apto", "motivo": "Encharcamiento y raíz sensible a hongos del suelo.", "fuente": "Ficha curada AgroPlan"}, "limoso": {"veredicto": "condicionado", "motivo": "Vigilar compactación y drenaje.", "fuente": "Ficha curada AgroPlan"}}'),
)


def upgrade() -> None:
    """Upgrade schema."""
    for codigo, kc, densidad, profundidad, aptitud in FICHAS:
        op.execute(
            sa.text(
                "UPDATE cultivos SET kc = :kc, densidad_plantas_m2 = :densidad, "
                "profundidad_raiz_cm = :profundidad, aptitud_suelo = :aptitud "
                "WHERE codigo = :codigo"
            ).bindparams(
                kc=kc,
                densidad=densidad,
                profundidad=profundidad,
                aptitud=aptitud,
                codigo=codigo,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    codigos = ", ".join(f"'{codigo}'" for codigo, *_ in FICHAS)
    op.execute(
        sa.text(
            f"UPDATE cultivos SET kc = NULL, densidad_plantas_m2 = NULL, "
            f"profundidad_raiz_cm = NULL, aptitud_suelo = NULL WHERE codigo IN ({codigos})"
        )
    )
