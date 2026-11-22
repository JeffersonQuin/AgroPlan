"""Migración de las fases de la corrida del agente.

Agrega ``fase`` y ``fase_desde`` a ``agente_corridas``: aditiva, nullable y sin tocar
las filas existentes. Se prueba sobre un SQLite temporal, no contra la base de
desarrollo.
"""

import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import settings

COLUMNAS_NUEVAS = ("fase", "fase_desde")
# Revisión previa a esta migración: el downgrade baja exactamente un paso.
REVISION_SIN_FASES = "c9e3f6a1d742"
RAIZ_BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture()
def migracion(tmp_path, monkeypatch):
    ruta = tmp_path / "fases.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{ruta}")
    configuracion = Config(str(RAIZ_BACKEND / "alembic.ini"))
    configuracion.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    return configuracion, ruta


def _columnas(ruta) -> dict[str, tuple]:
    conexion = sqlite3.connect(ruta)
    try:
        return {
            fila[1]: fila
            for fila in conexion.execute("pragma table_info(agente_corridas)")
        }
    finally:
        conexion.close()


def _ids(ruta) -> list[str]:
    conexion = sqlite3.connect(ruta)
    try:
        return [fila[0] for fila in conexion.execute("select id from agente_corridas")]
    finally:
        conexion.close()


def _fases(ruta) -> list[tuple]:
    conexion = sqlite3.connect(ruta)
    try:
        return conexion.execute("select fase, fase_desde from agente_corridas").fetchall()
    finally:
        conexion.close()


def _insertar_corrida(ruta, corrida_id: str) -> None:
    conexion = sqlite3.connect(ruta)
    try:
        conexion.execute(
            "insert into agente_corridas (id, proyecto_id, usuario_id, estado, entrada, "
            "intake_hash, motor_version, prompt_version, fase, fase_desde) values "
            "(?, ?, 1, 'ok', '{}', ?, 'v1', 'v4', 'precios', "
            "'2026-01-01 00:00:00')",
            (
                corrida_id,
                "11111111-1111-1111-1111-111111111111",
                "a" * 64,
            ),
        )
        conexion.commit()
    finally:
        conexion.close()


def test_upgrade_agrega_las_columnas_nullable(migracion) -> None:
    configuracion, ruta = migracion
    command.upgrade(configuracion, "head")

    columnas = _columnas(ruta)
    assert all(nueva in columnas for nueva in COLUMNAS_NUEVAS)
    for nueva in COLUMNAS_NUEVAS:
        assert columnas[nueva][3] == 0  # notnull


def test_downgrade_conserva_las_filas_y_el_upgrade_vuelve(migracion) -> None:
    configuracion, ruta = migracion
    command.upgrade(configuracion, "head")
    _insertar_corrida(ruta, "22222222-2222-2222-2222-222222222222")
    assert _ids(ruta) == ["22222222-2222-2222-2222-222222222222"]

    command.downgrade(configuracion, REVISION_SIN_FASES)

    columnas = _columnas(ruta)
    assert all(nueva not in columnas for nueva in COLUMNAS_NUEVAS)
    assert _ids(ruta) == ["22222222-2222-2222-2222-222222222222"]

    command.upgrade(configuracion, "head")

    assert _ids(ruta) == ["22222222-2222-2222-2222-222222222222"]
    # La fila sobrevive; las fases vuelven en NULL, como una corrida vieja.
    assert _fases(ruta) == [(None, None)]
