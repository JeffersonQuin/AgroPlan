"""Migración `c4e9a1b73f21`: origen, revisión y fuentes de las fichas de cultivo.

Cubre T12 de la ampliación: la migración es aditiva, marca todo lo sembrado como
`humano`, sobrevive a un downgrade sin perder filas y es no-op sobre una base ya
migrada. Corre contra un SQLite temporal por test, no contra la base de desarrollo.
"""

import hashlib
import sqlite3

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import settings

COLUMNAS_NUEVAS = ("origen", "revisado_en", "fuentes")


@pytest.fixture()
def migracion(tmp_path, monkeypatch):
    ruta = tmp_path / "catalogo.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{ruta}")
    configuracion = Config("alembic.ini")
    configuracion.set_main_option("script_location", "alembic")
    return configuracion, ruta


def _filas(ruta) -> list[tuple]:
    conexion = sqlite3.connect(ruta)
    try:
        return conexion.execute(
            "select codigo, origen, revisado_en, fuentes from cultivos"
        ).fetchall()
    finally:
        conexion.close()


def _columnas(ruta) -> list[str]:
    conexion = sqlite3.connect(ruta)
    try:
        return [fila[1] for fila in conexion.execute("pragma table_info(cultivos)")]
    finally:
        conexion.close()


def _ddl(ruta) -> str:
    conexion = sqlite3.connect(ruta)
    try:
        return conexion.execute(
            "select sql from sqlite_master where name='cultivos'"
        ).fetchone()[0]
    finally:
        conexion.close()


def test_upgrade_marca_lo_sembrado_como_humano(migracion) -> None:
    configuracion, ruta = migracion
    command.upgrade(configuracion, "head")

    filas = _filas(ruta)
    assert len(filas) == 8
    assert {fila[1] for fila in filas} == {"humano"}
    assert all(fila[2] is None and fila[3] is None for fila in filas)
    assert "ck_cultivos_origen CHECK (origen IN ('humano', 'agente'))" in _ddl(ruta)


def test_downgrade_y_upgrade_conservan_las_filas(migracion) -> None:
    configuracion, ruta = migracion
    command.upgrade(configuracion, "head")
    command.downgrade(configuracion, "-1")

    columnas = _columnas(ruta)
    assert all(nueva not in columnas for nueva in COLUMNAS_NUEVAS)
    assert len(conexion_filas(ruta)) == 8

    command.upgrade(configuracion, "head")
    filas = _filas(ruta)
    assert len(filas) == 8
    assert {fila[1] for fila in filas} == {"humano"}


def conexion_filas(ruta) -> list[tuple]:
    conexion = sqlite3.connect(ruta)
    try:
        return conexion.execute("select codigo from cultivos").fetchall()
    finally:
        conexion.close()


def test_upgrade_es_noop_sobre_base_ya_migrada(migracion) -> None:
    configuracion, ruta = migracion
    command.upgrade(configuracion, "head")
    antes = hashlib.sha256(ruta.read_bytes()).hexdigest()

    command.upgrade(configuracion, "head")

    assert hashlib.sha256(ruta.read_bytes()).hexdigest() == antes


def test_el_downgrade_pierde_la_trazabilidad_pero_no_las_filas(migracion) -> None:
    """Aviso documentado: revertir borra `fuentes`/`revisado_en` y re-marca `humano`."""

    configuracion, ruta = migracion
    command.upgrade(configuracion, "head")

    conexion = sqlite3.connect(ruta)
    try:
        conexion.execute(
            "insert into cultivos (codigo, nombre, icono, color, "
            "demanda_agua_l_m2_dia, ciclo_dias, activo, origen, revisado_en, fuentes) "
            "values ('quinoa', 'Quinoa', 'Q', '#2E7D32', 2.5, 150, 1, 'agente', "
            "NULL, '[{\"url\": \"https://example.org\"}]')"
        )
        conexion.commit()
    finally:
        conexion.close()

    command.downgrade(configuracion, "-1")
    command.upgrade(configuracion, "head")

    filas = {fila[0]: fila for fila in _filas(ruta)}
    assert len(filas) == 9
    # La fila sobrevive, pero queda indistinguible de una curada: es el precio de
    # revertir la migración y está documentado en la ampliación del contrato.
    assert filas["quinoa"][1] == "humano"
    assert filas["quinoa"][2] is None
    assert filas["quinoa"][3] is None


def test_el_modelo_y_la_migracion_no_derivan(migracion) -> None:
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    from app.database import Base

    configuracion, ruta = migracion
    command.upgrade(configuracion, "head")

    engine = create_engine(f"sqlite+pysqlite:///{ruta}", future=True)
    try:
        with engine.connect() as conexion:
            contexto = MigrationContext.configure(
                conexion, opts={"compare_type": True}
            )
            diferencias = compare_metadata(contexto, Base.metadata)
    finally:
        engine.dispose()

    assert diferencias == []
