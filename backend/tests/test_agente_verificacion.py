"""Verificación de contrato del agente con teardown real de dependencias.

Complementa `test_agente_api.py`: acá la API corre contra un SQLite en archivo con el
``get_db`` de producción (sesión propia y ``close()`` en el ``finally``), que es el
escenario donde la tarea de fondo podía quedarse con una sesión ya cerrada. El resto
son bordes del contrato: ruta documentada de ``aplicar``, estado observable, reparto
con ocho cultivos y dominios del sistema de riego.
"""

from __future__ import annotations

import random
import uuid
from itertools import pairwise

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.agente.validacion import corregir, repartir_porcentajes
from app.database import Base, get_db
from app.dependencies import get_current_user
from app.main import app
from app.models.agente import AgenteCorrida, AgenteFuente, AgenteRecomendacion
from app.models.catalogo import Cultivo, Suelo
from app.models.proyecto_cultivo import ProyectoCultivo
from app.models.riego import Sector, SistemaRiego
from app.repository import agente_corrida as corrida_repo
from app.repository import proyecto as proyecto_repo
from app.schemas.agente import (
    CultivoRecomendado,
    EmisorRecomendado,
    EntradaAgente,
    PropuestaAgente,
    SistemaRecomendado,
)
from app.schemas.comun import Punto
from app.schemas.riego import EmisorIn, SistemaRiegoIn
from app.services import agente as agente_service
from tests.conftest import create_user

CULTIVOS = [
    ("papa", "Papa", 2.0, 120),
    ("lechuga", "Lechuga", 1.5, 65),
    ("maiz", "Maiz", 4.0, 140),
    ("tomate", "Tomate", 5.0, 110),
    ("cebolla", "Cebolla", 3.0, 150),
    ("zanahoria", "Zanahoria", 2.5, 100),
    ("poroto", "Poroto", 3.5, 95),
    ("zapallo", "Zapallo", 4.5, 130),
]

AREA_TERRENO = 200.0


def _seed(db: Session, cantidad: int = 8) -> None:
    db.add_all(
        [
            Cultivo(
                codigo=codigo,
                nombre=nombre,
                icono=nombre[:1],
                color="#4CAF50",
                demanda_agua_l_m2_dia=demanda,
                ciclo_dias=ciclo,
                activo=True,
            )
            for codigo, nombre, demanda, ciclo in CULTIVOS[:cantidad]
        ]
    )
    db.add(Suelo(codigo="franco", nombre="Franco", infiltracion_mm_h=12.0))
    db.commit()


def _proyecto(cliente: TestClient, cantidad: int = 2) -> str:
    proyecto = cliente.post("/proyectos", json={"nombre": "P", "zona": "Cuyo"})
    assert proyecto.status_code == 201, proyecto.text
    proyecto_id = proyecto.json()["id"]

    terreno = cliente.put(
        f"/proyectos/{proyecto_id}/terreno",
        json={
            "nombre_parcela": "L",
            "forma": "rectangulo",
            "vertices": [
                {"x": 0, "y": 0},
                {"x": 10, "y": 0},
                {"x": 10, "y": 20},
                {"x": 0, "y": 20},
            ],
            "suelo_codigo": "franco",
            "pendiente_pct": 2,
            "fuente_agua": "pozo",
        },
    )
    assert terreno.status_code == 200, terreno.text

    for indice in range(cantidad):
        bloque = cliente.post(
            f"/proyectos/{proyecto_id}/cultivos",
            json={
                "cultivo_codigo": CULTIVOS[indice][0],
                "modo": "porcentaje",
                "porcentaje": round(100 / cantidad, 2),
            },
        )
        assert bloque.status_code in (200, 201), bloque.text
    return proyecto_id


@pytest.fixture()
def produccion(tmp_path):
    """``get_db`` real: una sesión por request, cerrada en el ``finally``."""

    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'prod.db'}", future=True)
    Base.metadata.create_all(bind=engine)
    sesiones = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def get_db_real():
        db = sesiones()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = get_db_real

    db = sesiones()
    _seed(db)
    usuario = create_user(db, email="produccion@example.com")
    app.dependency_overrides[get_current_user] = lambda: usuario
    try:
        with TestClient(app) as cliente:
            yield cliente, sesiones
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.fixture()
def cliente_compartido(db_session: Session):
    """Peticiones y asserts contra la misma sesión en memoria."""

    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    usuario = create_user(db_session, email="compartido@example.com")
    _seed(db_session)
    app.dependency_overrides[get_current_user] = lambda: usuario
    try:
        with TestClient(app) as cliente:
            yield cliente, db_session
    finally:
        app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# Ciclo real de la corrida (teardown de dependencias incluido)
# --------------------------------------------------------------------------- #


def test_corrida_termina_ok_con_el_teardown_real(produccion) -> None:
    cliente, _ = produccion
    proyecto_id = _proyecto(cliente)

    inicio = cliente.post(f"/proyectos/{proyecto_id}/agente")
    assert inicio.status_code == 202, inicio.text

    detalle = cliente.get(
        f"/proyectos/{proyecto_id}/agente/corridas/{inicio.json()['corrida_id']}"
    ).json()
    assert detalle["estado"] == "ok", detalle["error_detalle"]
    assert detalle["duracion_ms"] is not None
    assert detalle["terminado_en"] is not None


def test_estado_corriendo_es_observable(produccion, monkeypatch) -> None:
    cliente, sesiones = produccion
    visto: dict[str, str] = {}
    original = agente_service._contexto_desde_corrida

    def contexto(db, proyecto, entrada):
        otra = sesiones()
        try:
            fila = otra.query(AgenteCorrida).order_by(
                AgenteCorrida.iniciado_en.desc()
            ).first()
            visto["estado"] = fila.estado
        finally:
            otra.close()
        return original(db, proyecto, entrada)

    monkeypatch.setattr(agente_service, "_contexto_desde_corrida", contexto)

    proyecto_id = _proyecto(cliente)
    inicio = cliente.post(f"/proyectos/{proyecto_id}/agente")
    detalle = cliente.get(
        f"/proyectos/{proyecto_id}/agente/corridas/{inicio.json()['corrida_id']}"
    ).json()

    assert visto["estado"] == "corriendo"
    assert detalle["estado"] == "ok"


def test_202_200_409_y_sin_duplicados(cliente_compartido) -> None:
    cliente, db = cliente_compartido
    proyecto_id = _proyecto(cliente)

    primera = cliente.post(f"/proyectos/{proyecto_id}/agente")
    assert primera.status_code == 202, primera.text
    assert primera.json()["estado"] == "pendiente"

    repetida = cliente.post(f"/proyectos/{proyecto_id}/agente")
    assert repetida.status_code == 200, repetida.text
    assert repetida.json()["corrida_id"] == primera.json()["corrida_id"]

    filas = db.scalars(
        select(AgenteCorrida).where(
            AgenteCorrida.proyecto_id == uuid.UUID(proyecto_id)
        )
    ).all()
    assert len(filas) == 1
    assert len({fila.intake_hash for fila in filas}) == 1


def test_corrida_en_curso_bloquea_el_intake(cliente_compartido) -> None:
    cliente, db = cliente_compartido
    proyecto_id = _proyecto(cliente)

    proyecto = proyecto_repo.get_by_id(db, uuid.UUID(proyecto_id))
    agente_service.iniciar_corrida(db, proyecto)  # queda pendiente, sin ejecutar

    respuesta = cliente.post(f"/proyectos/{proyecto_id}/agente")
    assert respuesta.status_code == 409, respuesta.text


def test_hash_sale_de_la_entrada_congelada(cliente_compartido) -> None:
    cliente, db = cliente_compartido
    proyecto_id = _proyecto(cliente)
    corrida_id = cliente.post(f"/proyectos/{proyecto_id}/agente").json()["corrida_id"]

    fila = db.get(AgenteCorrida, uuid.UUID(corrida_id))
    assert fila is not None
    recomputada = EntradaAgente.model_validate(fila.entrada).huella()
    assert fila.intake_hash == recomputada
    assert len(recomputada) == 64


def test_error_generico_termina_en_error(cliente_compartido, monkeypatch) -> None:
    cliente, _ = cliente_compartido
    proyecto_id = _proyecto(cliente)

    def boom(_contexto, on_fase=None):
        raise RuntimeError("falla inesperada del gateway")

    monkeypatch.setattr(agente_service, "ejecutar_agente", boom)

    corrida_id = cliente.post(f"/proyectos/{proyecto_id}/agente").json()["corrida_id"]
    detalle = cliente.get(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}"
    ).json()
    assert detalle["estado"] == "error"
    assert "falla inesperada" in (detalle["error_detalle"] or "")
    assert detalle["terminado_en"]
    assert detalle["salida"] is None

    # Un reintento después del error no reutiliza la corrida rota.
    monkeypatch.undo()
    reintento = cliente.post(f"/proyectos/{proyecto_id}/agente")
    assert reintento.status_code == 202
    assert reintento.json()["corrida_id"] != corrida_id


# --------------------------------------------------------------------------- #
# Sin escrituras antes de aplicar
# --------------------------------------------------------------------------- #


def test_nada_escribe_en_el_proyecto_antes_de_aplicar(cliente_compartido) -> None:
    cliente, db = cliente_compartido
    proyecto_id = _proyecto(cliente, cantidad=8)
    bloques_antes = [b["id"] for b in cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()]

    def contar(modelo) -> int:
        return db.scalar(select(func.count()).select_from(modelo))

    antes = {m.__name__: contar(m) for m in (ProyectoCultivo, SistemaRiego, Sector)}

    corrida_id = cliente.post(f"/proyectos/{proyecto_id}/agente").json()["corrida_id"]
    assert cliente.get(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}"
    ).json()["estado"] == "ok"

    despues = {m.__name__: contar(m) for m in (ProyectoCultivo, SistemaRiego, Sector)}
    assert antes == despues
    assert [b["id"] for b in cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()] == bloques_antes
    assert cliente.get(f"/proyectos/{proyecto_id}/riego").status_code == 404


# --------------------------------------------------------------------------- #
# Aplicar: ruta documentada y efectos
# --------------------------------------------------------------------------- #


def test_ruta_aplicar_documentada(cliente_compartido) -> None:
    cliente, _ = cliente_compartido
    proyecto_id = _proyecto(cliente)
    corrida_id = cliente.post(f"/proyectos/{proyecto_id}/agente").json()["corrida_id"]

    # La ruta que documenta el contrato, sin el proyecto en el path.
    documentada = cliente.post(f"/agente/corridas/{corrida_id}/aplicar")
    assert documentada.status_code == 200, documentada.text

    # Y la que cuelga del proyecto, para el wizard: existe y responde que ya está
    # aplicada, no 404.
    scoped = cliente.post(f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}/aplicar")
    assert scoped.status_code == 409, scoped.text
    assert "aplicada" in scoped.json()["detail"]


def test_aplicar_marca_todo_y_deja_la_corrida_vigente(cliente_compartido) -> None:
    cliente, db = cliente_compartido
    proyecto_id = _proyecto(cliente, cantidad=3)
    corrida_id = cliente.post(f"/proyectos/{proyecto_id}/agente").json()["corrida_id"]
    assert cliente.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}/aplicar"
    ).status_code == 200

    bloques = db.scalars(
        select(ProyectoCultivo).where(
            ProyectoCultivo.proyecto_id == uuid.UUID(proyecto_id)
        )
    ).all()
    assert sum(float(bloque.area_m2) for bloque in bloques) <= AREA_TERRENO

    sistemas = db.scalars(
        select(SistemaRiego).where(
            SistemaRiego.proyecto_id == uuid.UUID(proyecto_id)
        )
    ).all()
    assert len(sistemas) == 1

    recomendaciones = db.scalars(
        select(AgenteRecomendacion).where(
            AgenteRecomendacion.corrida_id == uuid.UUID(corrida_id)
        )
    ).all()
    assert recomendaciones
    assert all(fila.aplicada and fila.aplicada_en for fila in recomendaciones)

    proyecto = proyecto_repo.get_by_id(db, uuid.UUID(proyecto_id))
    assert str(proyecto.corrida_actual_id) == corrida_id


def test_aplicar_ocho_cultivos_no_excede_el_terreno(cliente_compartido) -> None:
    cliente, _ = cliente_compartido
    proyecto_id = _proyecto(cliente, cantidad=8)
    corrida_id = cliente.post(f"/proyectos/{proyecto_id}/agente").json()["corrida_id"]

    aplicar = cliente.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}/aplicar"
    )
    assert aplicar.status_code == 200, aplicar.text
    total = sum(bloque["area_m2"] for bloque in aplicar.json()["diseno"]["bloques"])
    balance = cliente.get(f"/proyectos/{proyecto_id}/cultivos/balance").json()

    assert len(aplicar.json()["diseno"]["bloques"]) == 8
    assert total <= AREA_TERRENO + 1e-6
    assert balance["asignado_m2"] <= AREA_TERRENO


def test_reparto_con_areas_fraccionarias(cliente_compartido) -> None:
    from app.core.config import settings as configuracion

    generador = random.Random(7)
    casos: list[tuple[list[float], float]] = []
    for total in (200.0, 3200.0, 1.0, 0.3, 999.99):
        casos.append(([total / 8] * 8, total))
        casos.append(([total / 8 * 0.999] * 8, total))
    for _ in range(2000):
        total = generador.choice([1.0, 7.0, 200.0, 333.33, 1000.0])
        cortes = sorted(generador.uniform(0, total) for _ in range(7))
        bordes = [0.0] + cortes + [total * generador.uniform(0.05, 1.0)]
        areas = [
            round(fin - inicio, generador.choice([2, 4, 6]))
            for inicio, fin in pairwise(bordes)
            if fin - inicio > 0
        ]
        if sum(areas) <= total:
            casos.append((areas, total))

    assert configuracion.AGENTE_API_KEY == ""
    for areas, total in casos:
        porcentajes = repartir_porcentajes(areas, total)
        assert len(porcentajes) == len(areas)
        assert all(round(valor, 2) == valor for valor in porcentajes), porcentajes
        assert sum(porcentajes) <= 100.0, (areas, total, porcentajes)

    # Y aunque se le pase una suma mayor al terreno, nunca devuelve más del 100%.
    assert sum(repartir_porcentajes([100.0] * 8, 300.0)) <= 100.0


# --------------------------------------------------------------------------- #
# Dominios del sistema de riego
# --------------------------------------------------------------------------- #


def test_tanque_fuera_de_dominio_se_corrige() -> None:
    cruda = PropuestaAgente(
        cultivos=[
            CultivoRecomendado(
                cultivo_codigo="papa",
                nombre="Papa",
                area_m2=100,
                demanda_l_m2_dia=2.0,
                justificacion="prueba",
            )
        ],
        sistema=SistemaRecomendado(
            tipo="goteo",
            emisor=EmisorRecomendado(tipo="gotero", caudal_lh=2, separacion_m=0.3),
            separacion_laterales_m=0.5,
            tanque_l=5_000_000,
            bomba_hp=1,
            num_sectores=1,
        ),
    )

    corregida = corregir(
        cruda,
        catalogo={
            "papa": {
                "nombre": "Papa",
                "color": "#4CAF50",
                "demanda_agua_l_m2_dia": 2.0,
                "ciclo_dias": 120,
            }
        },
        area_m2=AREA_TERRENO,
        total_fuentes=1,
    )
    assert corregida.sistema.tanque_l == 1_000_000
    assert any(alerta.codigo == "RIEGO_AJUSTADO" for alerta in corregida.advertencias)

    # El payload que arma aplicar_corrida valida contra el contrato real.
    SistemaRiegoIn(
        tipo=corregida.sistema.tipo,
        fuente_agua="pozo",
        tanque_l=corregida.sistema.tanque_l,
        bomba_hp=corregida.sistema.bomba_hp,
        emisor=EmisorIn(
            caudal_lh=corregida.sistema.emisor.caudal_lh,
            separacion_m=corregida.sistema.emisor.separacion_m,
        ),
        separacion_laterales_m=corregida.sistema.separacion_laterales_m,
        punto_conexion=Punto(x=0, y=0),
        num_sectores=corregida.sistema.num_sectores,
    )


def test_fallback_catalogo_con_fuentes_reales(cliente_compartido) -> None:
    cliente, db = cliente_compartido
    proyecto_id = _proyecto(cliente, cantidad=4)
    corrida_id = cliente.post(f"/proyectos/{proyecto_id}/agente").json()["corrida_id"]

    fila = corrida_repo.get_by_id(db, uuid.UUID(corrida_id))
    propuesta = PropuestaAgente.model_validate(fila.salida)
    fuentes = db.scalars(
        select(AgenteFuente).where(AgenteFuente.corrida_id == uuid.UUID(corrida_id))
    ).all()

    assert fila.estado == "ok"
    assert fila.modelo == "catalogo"
    assert fila.tokens_entrada is None
    assert len(fuentes) == 2
    for fuente in fuentes:
        assert fuente.tipo == "catalogo_interno"
        assert fuente.url and fuente.titulo
    for cultivo in propuesta.cultivos:
        assert cultivo.fuente_ids
        assert max(cultivo.fuente_ids) <= len(fuentes)
    assert sum(cultivo.area_m2 for cultivo in propuesta.cultivos) <= AREA_TERRENO
    assert any(
        alerta.codigo == "AGENTE_SIN_CREDENCIALES" for alerta in propuesta.advertencias
    )
