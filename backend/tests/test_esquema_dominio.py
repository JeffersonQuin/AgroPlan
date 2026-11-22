"""Esquema de dominio: migración reversible, catálogo sembrado e invariantes.

Cubre S1 (tablas), S2 (caudal efectivo con procedencia), S4 (el contrato del agente no
lleva geometría), S5 (el cliente no puede mandar áreas), S7 (huella del intake) y S9
(la misma revisión corre en SQLite y renderiza DDL para PostgreSQL).
"""

import contextlib
import sqlite3
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from app.core import config as config_mod
from app.models.agente import AgenteCorrida
from app.models.catalogo import Cultivo
from app.models.proyecto import Terreno
from app.schemas.agente import EntradaAgente, ProductoDeseado, PropuestaAgente
from app.schemas.proyecto import TerrenoIn, TerrenoUpdate

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
TABLAS_NUEVAS = {
    "agente_corridas",
    "agente_fuentes",
    "agente_recomendaciones",
    "cultivos",
    "materiales_precio",
    "proyecto_cultivos",
    "proyectos",
    "red_nodos",
    "red_tramos",
    "sector_bloques",
    "sectores",
    "sistemas_riego",
    "suelos",
    "terrenos",
}


def _cfg() -> Config:
    cfg = Config(str(RAIZ_BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    return cfg


def _tablas(ruta: Path) -> set[str]:
    con = sqlite3.connect(ruta)
    try:
        return {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    finally:
        con.close()


@pytest.fixture()
def base_url(tmp_path, monkeypatch) -> str:
    url = f"sqlite+pysqlite:///{tmp_path / 'migracion.db'}"
    monkeypatch.setattr(config_mod.settings, "DATABASE_URL", url)
    return url


@pytest.fixture()
def ruta_db(base_url) -> Path:
    return Path(base_url.split("///", 1)[1])


def test_migracion_ida_y_vuelta(base_url, ruta_db):  # S1, S9
    command.upgrade(_cfg(), "head")
    tablas = _tablas(ruta_db)
    assert TABLAS_NUEVAS <= tablas
    assert tablas == TABLAS_NUEVAS | {"usuarios", "alembic_version"}

    command.downgrade(_cfg(), "base")
    assert _tablas(ruta_db) == {"alembic_version"}

    command.upgrade(_cfg(), "head")
    assert TABLAS_NUEVAS <= _tablas(ruta_db)


def test_catalogo_sembrado(base_url):  # T5
    command.upgrade(_cfg(), "head")
    with Session(create_engine(base_url)) as sesion:
        assert sesion.query(Cultivo).count() == 8
        papa = sesion.get(Cultivo, "papa")
        assert papa.meses_siembra == [3, 9, 10, 11]
        # 4 suelos de la textura básica + 6 de las zonas productivas de Bolivia.
    assert sesion.execute(sa.text("select count(*) from suelos")).scalar_one() == 10
    assert sesion.execute(
        sa.text("select count(*) from suelos where codigo in "
                "('franco_arenoso', 'franco_arcilloso', 'salino', 'calcareo', "
                "'pedregoso', 'organico')")
    ).scalar_one() == 6


def test_check_caudal_coherente(base_url, ruta_db):  # S2
    command.upgrade(_cfg(), "head")
    con = sqlite3.connect(ruta_db)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute(
        "insert into usuarios (email, rol, activo, email_verificado)"
        " values ('esquema@example.com','usuario',1,0)"
    )
    usuario_id = con.execute("select id from usuarios where email='esquema@example.com'").fetchone()[0]
    # Commit del usuario antes de las pruebas de CHECK: ``rollback()`` las deshace y no
    # debe arrastrar el usuario, que es el padre de los proyectos.
    con.commit()

    def proyecto(nombre: str) -> str:
        proyecto_id = str(uuid.uuid4())
        con.execute(
            "insert into proyectos (id, usuario_id, nombre, unidad, estado, paso_actual,"
            " ultimo_paso_completado, version) values (?,?,?,?,?,?,?,?)",
            (proyecto_id, usuario_id, nombre, "metric", "borrador", 1, 1, 1),
        )
        return proyecto_id

    def terreno(proyecto_id: str, **extra) -> None:
        fila = {
            "id": str(uuid.uuid4()),
            "proyecto_id": proyecto_id,
            "nombre_parcela": "Lote",
            "forma": "rectangulo",
            "geometria": '{"vertices": [], "cerrado": true}',
            "area_m2": 100,
            "perimetro_m": 40,
            "lados": 4,
            "suelo_codigo": "franco",
            "pendiente_pct": 0,
            "fuente_agua": "pila",
            "caudal_efectivo_m3h": 2.0,
        }
        fila.update(extra)
        columnas = ",".join(fila)
        marcas = ",".join("?" for _ in fila)
        con.execute(f"insert into terrenos ({columnas}) values ({marcas})", tuple(fila.values()))

    try:
        with pytest.raises(sqlite3.IntegrityError, match="ck_terrenos_caudal_coherente"):
            terreno(proyecto("incoherente"), caudal_origen="cliente", caudal_base_fuente=None)
        con.rollback()

        terreno(proyecto("asumido"), caudal_origen="asumido", caudal_base_fuente="pila")
        terreno(
            proyecto("cliente"),
            caudal_origen="cliente",
            caudal_disponible_m3h=3.5,
            caudal_base_fuente=None,
        )
        con.commit()
    finally:
        con.close()


def test_ddl_postgresql_portable(tmp_path, monkeypatch):  # S9
    monkeypatch.setattr(
        config_mod.settings, "DATABASE_URL", "postgresql+psycopg2://u:p@localhost:5432/x"
    )
    salida = tmp_path / "postgres.sql"
    with salida.open("w") as destino, contextlib.redirect_stdout(destino):
        command.upgrade(_cfg(), "head", sql=True)
    sql = salida.read_text()
    assert sql.count("CREATE TABLE") == 16
    assert "JSONB" in sql and "UUID" in sql
    assert "ARRAY" not in sql and "gen_random_uuid" not in sql


def test_terreno_in_prohibe_areas_del_cliente():  # S5
    base = {
        "nombre_parcela": "Lote",
        "vertices": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}],
        "suelo_codigo": "franco",
        "fuente_agua": "pozo",
    }
    assert TerrenoIn(**base).caudal_disponible_m3h is None
    for campo in ("area_m2", "perimetro_m", "lados"):
        with pytest.raises(ValidationError):
            TerrenoIn(**base, **{campo: 1.0})


def test_propuesta_agente_sin_geometria():  # S4
    valida = {
        "cultivos": [
            {
                "cultivo_codigo": "papa",
                "nombre": "Papa",
                "area_m2": 50,
                "demanda_l_m2_dia": 2.0,
                "justificacion": "Suelo franco y ciclo compatible.",
            }
        ],
        "sistema": {
            "emisor": {"caudal_lh": 4, "separacion_m": 0.3},
            "separacion_laterales_m": 0.8,
            "bomba_hp": 1,
            "num_sectores": 2,
        },
    }
    assert PropuestaAgente(**valida)
    for campo in ("poligono", "geometria", "vertices", "red", "sectores", "computo"):
        with pytest.raises(ValidationError):
            PropuestaAgente(**valida, **{campo: "x"})


def test_huella_intake_estable_y_sensible():  # S7
    def entrada(caudal: float) -> EntradaAgente:
        return EntradaAgente(
            proyecto_id=uuid.UUID(int=1),
            productos=[ProductoDeseado(nombre="Papa")],
            area_m2=100,
            suelo_codigo="franco",
            fuente_agua="pozo",
            caudal_efectivo_m3h=caudal,
            caudal_origen="asumido",
            zona="Cuyo",
        )

    huella = entrada(2.0).huella()
    assert len(huella) == 64
    assert huella == entrada(2.0).huella()
    assert huella != entrada(2.5).huella()
    assert "intake_hash" in AgenteCorrida.__table__.columns


def test_terreno_persiste_caudal_efectivo_y_origen():  # S2
    columnas = Terreno.__table__.c
    assert not columnas.caudal_efectivo_m3h.nullable
    assert {"caudal_origen", "caudal_base_fuente", "caudal_actualizado_en"} <= set(columnas.keys())


def test_terreno_update_tri_estado_del_caudal():  # S2, editabilidad
    assert not TerrenoUpdate().limpia_caudal
    assert TerrenoUpdate(caudal_disponible_m3h=None).limpia_caudal
    edicion = TerrenoUpdate(caudal_disponible_m3h=0.9)
    assert not edicion.limpia_caudal and edicion.caudal_disponible_m3h == 0.9
    assert "suelo_codigo" not in edicion.model_fields_set
