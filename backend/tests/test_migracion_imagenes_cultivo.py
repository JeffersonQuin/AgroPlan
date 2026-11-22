"""Migraciones de las imágenes de la ficha curada al catálogo de cultivos (T3, S4).

Cubre que `f5a2c8d9e310` agregue las tres columnas y copie imagen, fuente y crédito,
que la migración de datos posterior re-sincronice una base que ya se había migrado con
las fichas vacías y que su `upgrade` repetido no rompa ni duplique. Corre contra un
SQLite temporal por test, no contra la base de desarrollo.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.agente import fichas as fichas_agente
from app.core.config import settings

# La suite se puede correr desde `backend/` o desde la raíz del repo: las rutas de
# alembic se resuelven contra el paquete, no contra el directorio actual.
RAIZ_BACKEND = Path(__file__).resolve().parents[1]
IMAGEN = "https://fichas.example/papa.jpg"
FUENTE = "https://fichas.example/papa"
CREDITO = "Foto: Scott Bauer, USDA ARS / Wikimedia Commons, dominio público"
# Revisión que agrega las columnas y la que las quita, para probar el downgrade sin
# depender de cuántas migraciones haya encima.
REVISION_COLUMNAS = "f5a2c8d9e310"
REVISION_SIN_COLUMNAS = "b4f7a2c9d1e8"


@pytest.fixture()
def migracion(tmp_path, monkeypatch):
    ruta = tmp_path / "catalogo.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{ruta}")
    configuracion = Config(str(RAIZ_BACKEND / "alembic.ini"))
    configuracion.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    return configuracion, ruta


@pytest.fixture()
def ficha_con_imagen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directorio = tmp_path / "fichas"
    directorio.mkdir()
    (directorio / "papa.json").write_text(
        json.dumps(
            {
                "codigo": "papa",
                "nombre": "Papa",
                "icono": "P",
                "color": "#8D6E63",
                "demanda_agua_l_m2_dia": 2.0,
                "ciclo_dias": 120,
                "meses_siembra": [3, 4, 9, 10],
                "notas": "Ficha de prueba con imagen.",
                "fuentes": [
                    {
                        "tipo": "manual",
                        "titulo": "Ficha técnica curada AgroPlan",
                        "url": None,
                        "fragmento": "Demanda y ciclo del catálogo base",
                    }
                ],
                "imagen": IMAGEN,
                "imagen_fuente": FUENTE,
                "imagen_credito": CREDITO,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(fichas_agente, "DIRECTORIO_FICHAS", directorio)
    fichas_agente._cargar.cache_clear()
    try:
        yield directorio
    finally:
        fichas_agente._cargar.cache_clear()


def _columnas(ruta) -> list[str]:
    conexion = sqlite3.connect(ruta)
    try:
        return [fila[1] for fila in conexion.execute("pragma table_info(cultivos)")]
    finally:
        conexion.close()


def _imagen(ruta, codigo: str) -> tuple[str | None, str | None, str | None]:
    conexion = sqlite3.connect(ruta)
    try:
        return conexion.execute(
            "select imagen_url, imagen_fuente_url, imagen_credito "
            "from cultivos where codigo = ?",
            (codigo,),
        ).fetchone()
    finally:
        conexion.close()


def _vaciar_imagen(ruta, codigo: str) -> None:
    conexion = sqlite3.connect(ruta)
    try:
        conexion.execute(
            "update cultivos set imagen_url = NULL, imagen_fuente_url = NULL, "
            "imagen_credito = NULL where codigo = ?",
            (codigo,),
        )
        conexion.commit()
    finally:
        conexion.close()


def _filas(ruta, *columnas: str) -> list[tuple]:
    conexion = sqlite3.connect(ruta)
    try:
        return conexion.execute(
            f"select {', '.join(columnas)} from cultivos"
        ).fetchall()
    finally:
        conexion.close()


def test_upgrade_agrega_las_columnas_y_copia_la_ficha(
    migracion, ficha_con_imagen
) -> None:
    configuracion, ruta = migracion
    command.upgrade(configuracion, "head")

    assert {"imagen_url", "imagen_fuente_url", "imagen_credito"} <= set(
        _columnas(ruta)
    )
    assert _imagen(ruta, "papa") == (IMAGEN, FUENTE, CREDITO)
    # Los cultivos sin imagen curada quedan en null, no con un valor inventado.
    assert _imagen(ruta, "lechuga") == (None, None, None)


def test_la_migracion_de_datos_resincroniza_una_fila_que_quedo_en_null(
    migracion, ficha_con_imagen
) -> None:
    configuracion, ruta = migracion
    # Base que ya corrió la revisión de columnas cuando las fichas no tenían URLs.
    command.upgrade(configuracion, REVISION_COLUMNAS)
    _vaciar_imagen(ruta, "papa")
    assert _imagen(ruta, "papa") == (None, None, None)

    command.upgrade(configuracion, "head")
    assert _imagen(ruta, "papa") == (IMAGEN, FUENTE, CREDITO)
    assert len(_filas(ruta, "codigo")) == 8

    # Repetir el upgrade no rompe ni duplica: la migración de datos es idempotente.
    command.upgrade(configuracion, "head")
    assert _imagen(ruta, "papa") == (IMAGEN, FUENTE, CREDITO)
    assert len(_filas(ruta, "codigo")) == 8


def test_downgrade_y_upgrade_conservan_las_filas(migracion, ficha_con_imagen) -> None:
    configuracion, ruta = migracion
    command.upgrade(configuracion, "head")
    command.downgrade(configuracion, REVISION_SIN_COLUMNAS)

    columnas = _columnas(ruta)
    assert "imagen_url" not in columnas
    assert "imagen_fuente_url" not in columnas
    assert "imagen_credito" not in columnas
    assert len(_filas(ruta, "codigo")) == 8

    command.upgrade(configuracion, "head")
    assert len(_filas(ruta, "codigo")) == 8
    assert _imagen(ruta, "papa") == (IMAGEN, FUENTE, CREDITO)

    # Revertir la migración de datos no borra lo sincronizado: es solo un resync.
    command.downgrade(configuracion, REVISION_COLUMNAS)
    assert _imagen(ruta, "papa") == (IMAGEN, FUENTE, CREDITO)
    assert len(_filas(ruta, "codigo")) == 8
