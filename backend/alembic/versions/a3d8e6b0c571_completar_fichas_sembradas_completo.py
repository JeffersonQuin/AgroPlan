"""completar las fichas sembradas con sus datos agronómicos

La migración c4e9a1b73f21 agregó `kc` y `aptitud_suelo`, y d7a1e4c9b2f0 el resto de la
ficha agronómica, pero las ocho filas sembradas del catálogo quedaron con esas columnas
vacías: el paso 2 mostraba "sin dato" para todos los cultivos que ya existían.

Esta migración copia las fichas curadas del repo (`app/agente/fichas/`) a las filas
sembradas, incluidas las seis nuevas (`vid`, `trigo`, `zanahoria`, `cebolla`) y la
aptitud para los diez suelos del catálogo.

Los valores se generaron leyendo las fichas, no transcribiéndolos a mano.

Revision ID: a3d8e6b0c571
Revises: f2b7c9d4e610
Create Date: 2026-11-22 01:47:12.905114

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a3d8e6b0c571"
down_revision: str | Sequence[str] | None = "f2b7c9d4e610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# codigo, kc, plantas/m2, raiz cm, aptitud por suelo
FICHAS: tuple[tuple[str, float, float, int, str], ...] = (
    ("papa", 1.15, 4.0, 40, '{"arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Drenaje lento: riesgo alto de pudrición del tubérculo.", "veredicto": "no_apto"}, "arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Drena rápido y retiene poco: regar en pulsos más frecuentes.", "veredicto": "condicionado"}, "calcareo": {"fuente": "Ficha curada AgroPlan", "motivo": "pH alto: puede faltar zinc y fósforo disponible.", "veredicto": "condicionado"}, "franco": {"fuente": "Ficha curada AgroPlan", "motivo": "Suelo equilibrado en drenaje y retención; ideal para tubérculo.", "veredicto": "apto"}, "franco_arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Retiene mucho: cuidar el riego para evitar pudrición.", "veredicto": "condicionado"}, "franco_arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Suelto y con buen drenaje: ideal para el tubérculo.", "veredicto": "apto"}, "limoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Buena retención pero se compacta: cuidar laboreo.", "veredicto": "condicionado"}, "organico": {"fuente": "Ficha curada AgroPlan", "motivo": "Buena fertilidad y estructura para el cultivo.", "veredicto": "apto"}, "pedregoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Las piedras deforman el tubérculo en la cosecha.", "veredicto": "no_apto"}, "salino": {"fuente": "Ficha curada AgroPlan", "motivo": "La papa es sensible a la salinidad del suelo.", "veredicto": "no_apto"}}'),
    ("lechuga", 1.0, 9.0, 20, '{"arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Puede encharcar: vigilar drenaje y hongos.", "veredicto": "condicionado"}, "arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Retiene poco: aumentar frecuencia de riego.", "veredicto": "condicionado"}, "calcareo": {"fuente": "Ficha curada AgroPlan", "motivo": "Puede amarillear por falta de hierro.", "veredicto": "condicionado"}, "franco": {"fuente": "Ficha curada AgroPlan", "motivo": "Suelo ideal: humedad pareja y buen drenaje.", "veredicto": "apto"}, "franco_arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Retiene humedad de más: vigilar hongos.", "veredicto": "condicionado"}, "franco_arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Drena bien y permite raíces superficiales sanas.", "veredicto": "apto"}, "limoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Alta retención con buen manejo de riego.", "veredicto": "apto"}, "organico": {"fuente": "Ficha curada AgroPlan", "motivo": "Alta fertilidad, ideal para hoja.", "veredicto": "apto"}, "pedregoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Raíz superficial: molesta en siembra y cosecha.", "veredicto": "condicionado"}, "salino": {"fuente": "Ficha curada AgroPlan", "motivo": "Muy sensible a la salinidad.", "veredicto": "no_apto"}}'),
    ("tomate", 1.1, 2.5, 60, '{"arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Encharcamiento y raíz sensible a hongos del suelo.", "veredicto": "no_apto"}, "arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Riego más frecuente; sensible a estrés hídrico.", "veredicto": "condicionado"}, "calcareo": {"fuente": "Ficha curada AgroPlan", "motivo": "pH alto: puede bloquear micronutrientes.", "veredicto": "condicionado"}, "franco": {"fuente": "Ficha curada AgroPlan", "motivo": "Suelo ideal para el cultivo.", "veredicto": "apto"}, "franco_arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Riesgo de encharcamiento y hongos del suelo.", "veredicto": "condicionado"}, "franco_arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Drenaje rápido, bueno para raíz sensible.", "veredicto": "apto"}, "limoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Vigilar compactación y drenaje.", "veredicto": "condicionado"}, "organico": {"fuente": "Ficha curada AgroPlan", "motivo": "Fértil, con buen manejo de humedad.", "veredicto": "apto"}, "pedregoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Raíz profunda; piedras en el perfil limitan.", "veredicto": "condicionado"}, "salino": {"fuente": "Ficha curada AgroPlan", "motivo": "Moderadamente tolerante, con manejo.", "veredicto": "condicionado"}}'),
    ("maiz", 1.2, 7.0, 80, '{"arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Drenaje lento: riesgo de anegamiento temprano.", "veredicto": "condicionado"}, "arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Requiere riegos más frecuentes por baja retención.", "veredicto": "condicionado"}, "calcareo": {"fuente": "Ficha curada AgroPlan", "motivo": "Vigilar zinc y hierro.", "veredicto": "condicionado"}, "franco": {"fuente": "Ficha curada AgroPlan", "motivo": "Perfil profundo y equilibrado para el sistema radical.", "veredicto": "apto"}, "franco_arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Retiene agua para el ciclo largo.", "veredicto": "apto"}, "franco_arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Buen perfil para el sistema radical.", "veredicto": "apto"}, "limoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Buena reserva de agua para el ciclo.", "veredicto": "apto"}, "organico": {"fuente": "Ficha curada AgroPlan", "motivo": "Buena fertilidad; cuidado con el exceso de nitrógeno.", "veredicto": "apto"}, "pedregoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Raíz profunda: piedras en el perfil limitan.", "veredicto": "condicionado"}, "salino": {"fuente": "Ficha curada AgroPlan", "motivo": "Tolera algo de sal, con rendimiento menor.", "veredicto": "condicionado"}}'),
    ("vid", 0.8, 0.4, 100, '{"arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Riesgo de asfixia radicular.", "veredicto": "condicionado"}, "arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Drena rápido: regar más seguido.", "veredicto": "condicionado"}, "calcareo": {"fuente": "Ficha curada AgroPlan", "motivo": "Riesgo de clorosis férrica.", "veredicto": "condicionado"}, "franco": {"fuente": "Ficha curada AgroPlan", "motivo": "Suelo equilibrado para el cultivo.", "veredicto": "apto"}, "franco_arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Retiene de más; controlar el riego.", "veredicto": "condicionado"}, "franco_arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Suelto y cálido, bueno para la maduración.", "veredicto": "apto"}, "limoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Vigilar compactación.", "veredicto": "condicionado"}, "organico": {"fuente": "Ficha curada AgroPlan", "motivo": "Mucho vigor: controlar para no perder calidad.", "veredicto": "condicionado"}, "pedregoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Suelos pedregosos son tradicionales en vid.", "veredicto": "apto"}, "salino": {"fuente": "Ficha curada AgroPlan", "motivo": "Tolera algo de sal según portainjerto.", "veredicto": "condicionado"}}'),
    ("trigo", 1.15, 200, 70, '{"arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Puede anegarse en emergencia.", "veredicto": "condicionado"}, "arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Reserva de agua baja: asegurar riegos.", "veredicto": "condicionado"}, "calcareo": {"fuente": "Ficha curada AgroPlan", "motivo": "Vigilar disponibilidad de fósforo y zinc.", "veredicto": "condicionado"}, "franco": {"fuente": "Ficha curada AgroPlan", "motivo": "Suelo ideal para el cultivo.", "veredicto": "apto"}, "franco_arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Reserva adecuada para el llenado.", "veredicto": "apto"}, "franco_arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Buen drenaje y laboreo.", "veredicto": "apto"}, "limoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Buena reserva de agua para el ciclo.", "veredicto": "apto"}, "organico": {"fuente": "Ficha curada AgroPlan", "motivo": "Exceso de nitrógeno provoca vuelco.", "veredicto": "condicionado"}, "pedregoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Molesta en laboreo y cosecha.", "veredicto": "condicionado"}, "salino": {"fuente": "Ficha curada AgroPlan", "motivo": "Tolera salinidad moderada.", "veredicto": "condicionado"}}'),
    ("zanahoria", 1.05, 100, 30, '{"arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Duro y pesado: deforma la raíz.", "veredicto": "no_apto"}, "arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Suelto: raíces rectas y parejas.", "veredicto": "apto"}, "calcareo": {"fuente": "Ficha curada AgroPlan", "motivo": "Puede faltar boro y fósforo.", "veredicto": "condicionado"}, "franco": {"fuente": "Ficha curada AgroPlan", "motivo": "Suelo ideal para la raíz.", "veredicto": "apto"}, "franco_arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Puede deformar; cuidar la preparación.", "veredicto": "condicionado"}, "franco_arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Excelente para raíz pivotante.", "veredicto": "apto"}, "limoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Se compacta y deforma la raíz.", "veredicto": "condicionado"}, "organico": {"fuente": "Ficha curada AgroPlan", "motivo": "Suelto y fértil; evitar estiércol fresco.", "veredicto": "apto"}, "pedregoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Las piedras deforman la raíz comercial.", "veredicto": "no_apto"}, "salino": {"fuente": "Ficha curada AgroPlan", "motivo": "Sensible; vigilar el desarrollo.", "veredicto": "condicionado"}}'),
    ("cebolla", 1.05, 60, 25, '{"arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Retiene de más: riesgo de pudrición del bulbo.", "veredicto": "condicionado"}, "arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Buen drenaje, menos riesgo de pudrición.", "veredicto": "apto"}, "calcareo": {"fuente": "Ficha curada AgroPlan", "motivo": "Vigilar azufre y micronutrientes.", "veredicto": "condicionado"}, "franco": {"fuente": "Ficha curada AgroPlan", "motivo": "Suelo ideal para el bulbo.", "veredicto": "apto"}, "franco_arcilloso": {"fuente": "Ficha curada AgroPlan", "motivo": "Buena reserva; cuidar el drenaje al final.", "veredicto": "apto"}, "franco_arenoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Equilibrado, fácil de cosechar.", "veredicto": "apto"}, "limoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Buena retención con manejo cuidadoso.", "veredicto": "apto"}, "organico": {"fuente": "Ficha curada AgroPlan", "motivo": "Fértil; evitar materia orgánica fresca.", "veredicto": "apto"}, "pedregoso": {"fuente": "Ficha curada AgroPlan", "motivo": "Molesta en la cosecha del bulbo.", "veredicto": "condicionado"}, "salino": {"fuente": "Ficha curada AgroPlan", "motivo": "Tolera algo de sal según variedad.", "veredicto": "condicionado"}}'),
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
