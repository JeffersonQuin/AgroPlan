"""Tipos de columna comunes del dominio AgroPlan.

El backend corre en SQLite durante el desarrollo (ver ``app/core/config.example.py``)
y en PostgreSQL en producción. Estos alias mantienen un único modelo para ambas
bases: ``jsonb`` en PostgreSQL, ``JSON`` en SQLite.
"""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

JSONB_TIPO = JSON().with_variant(JSONB(), "postgresql")


def check_en(columna: str, valores: tuple[str, ...]) -> str:
    """Arma el texto de un CHECK ``columna IN (...)`` a partir de un dominio.

    Mantiene el dominio en un único lugar (``app/models/enums.py``): si se agrega
    un valor al enum, el CHECK de la tabla lo hereda sin editar el modelo.
    """

    lista = ", ".join(f"'{valor}'" for valor in valores)
    return f"{columna} IN ({lista})"


__all__ = ["JSONB_TIPO", "check_en"]
