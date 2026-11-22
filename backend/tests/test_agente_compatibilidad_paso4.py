"""Compatibilidad del contrato del agente: corridas y bodies previos al paso 4.

Cubre S5 (restricciones congeladas y datos ausentes en null), el riesgo de
compatibilidad de la salida vieja (defaults de Pydantic) y la idempotencia del intake.
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.main import app
from app.models.agente import AgenteCorrida
from app.models.catalogo import Cultivo, Suelo
from app.models.proyecto import Proyecto
from app.models.usuario import Usuario
from tests.conftest import create_user

ENTRADA_VIEJA = {
    "productos": [{"nombre": "Papa", "prioridad": 1}],
    "area_m2": 200.0,
    "suelo_codigo": "franco",
    "fuente_agua": "pozo",
    "caudal_efectivo_m3h": 1.5,
    "caudal_origen": "asumido",
    "zona": "Cuyo",
    "pendiente_pct": 2.0,
}
SALIDA_VIEJA = {
    "cultivos": [
        {
            "cultivo_codigo": "papa",
            "nombre": "Papa",
            "area_m2": 200.0,
            "demanda_l_m2_dia": 2.0,
            "justificacion": "congelada antes del paso 4",
        }
    ],
    "sistema": {
        "tipo": "goteo",
        "emisor": {"tipo": "gotero", "caudal_lh": 2.0, "separacion_m": 0.3},
        "separacion_laterales_m": 0.5,
        "bomba_hp": 1.0,
        "num_sectores": 1,
    },
    "advertencias": [],
}


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="compat4@example.com")


@pytest.fixture()
def cliente_autenticado(client: TestClient, usuario: Usuario) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_current_user] = lambda: usuario
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def catalogo(db_session: Session) -> None:
    db_session.add_all(
        [
            Cultivo(
                codigo="papa",
                nombre="Papa",
                icono="P",
                color="#8D6E63",
                demanda_agua_l_m2_dia=2.0,
                ciclo_dias=120,
                kc=1.15,
                profundidad_raiz_cm=40,
                densidad_plantas_m2=4.0,
                meses_siembra=[3, 4],
                aptitud_suelo={
                    "franco": {"veredicto": "apto", "motivo": "ok", "fuente": "f"}
                },
                activo=True,
            ),
            Suelo(codigo="franco", nombre="Franco", infiltracion_mm_h=12.0),
        ]
    )
    db_session.commit()


def _proyecto(cliente: TestClient) -> str:
    pid = cliente.post("/proyectos", json={"nombre": "P", "zona": "Cuyo"}).json()["id"]
    terreno = cliente.put(
        f"/proyectos/{pid}/terreno",
        json={
            "nombre_parcela": "Lote 1",
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
    bloque = cliente.post(
        f"/proyectos/{pid}/cultivos",
        json={"cultivo_codigo": "papa", "modo": "porcentaje", "porcentaje": 100},
    )
    assert bloque.status_code == 201, bloque.text
    return pid


def _corrida_vieja(pid: str, db_session: Session) -> AgenteCorrida:
    corrida = AgenteCorrida(
        proyecto_id=uuid.UUID(pid),
        usuario_id=db_session.get(Proyecto, uuid.UUID(pid)).usuario_id,
        estado="ok",
        entrada=dict(ENTRADA_VIEJA, proyecto_id=pid),
        salida=SALIDA_VIEJA,
        intake_hash="hash-anterior-al-paso-4",
        motor_version="m1",
        prompt_version="v1",
    )
    db_session.add(corrida)
    db_session.commit()
    return corrida


def test_corrida_vieja_sin_campos_nuevos_se_devuelve_sin_500(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida_vieja(pid, db_session)

    for url in (
        f"/proyectos/{pid}/agente/corridas/{corrida.id}",
        f"/agente/corridas/{corrida.id}",
    ):
        respuesta = cliente.get(url)
        assert respuesta.status_code == 200, respuesta.text
        salida = respuesta.json()["salida"]
        assert salida["cifras"]["turnos"] == []
        assert salida["materiales"] == []
        assert salida["recomendaciones"] == []
        assert salida["cultivos"][0]["imagen_url"] is None

    aplicar = cliente.post(f"/proyectos/{pid}/agente/corridas/{corrida.id}/aplicar")
    assert aplicar.status_code == 200, aplicar.text


def test_mismo_intake_reutiliza_y_las_restricciones_generan_otra(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)

    primera = cliente.post(f"/proyectos/{pid}/agente", json={})
    assert primera.status_code == 202, primera.text
    repetida = cliente.post(f"/proyectos/{pid}/agente", json={})
    assert repetida.status_code == 200, repetida.text
    assert repetida.json()["corrida_id"] == primera.json()["corrida_id"]

    con_restricciones = cliente.post(
        f"/proyectos/{pid}/agente",
        json={"restricciones": {"energia": "solar", "tanque_l": 5000}},
    )
    assert con_restricciones.status_code == 202, con_restricciones.text
    assert con_restricciones.json()["corrida_id"] != primera.json()["corrida_id"]

    por_alias = cliente.post(
        f"/proyectos/{pid}/agente/corridas",
        json={"restricciones": {"energia": "solar", "tanque_l": 5000}},
    )
    assert por_alias.status_code == 200, por_alias.text
    assert por_alias.json()["corrida_id"] == con_restricciones.json()["corrida_id"]


def test_bodies_previos_siguen_aceptandose_y_el_alias_congela_restricciones(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado

    sin_body_pid = _proyecto(cliente)
    assert cliente.post(f"/proyectos/{sin_body_pid}/agente").status_code == 202

    viejo_pid = _proyecto(cliente)
    viejo = cliente.post(
        f"/proyectos/{viejo_pid}/agente",
        json={
            "siembra": "2026-11-20",
            "productos": [{"cultivo_codigo": "papa", "prioridad": 1}],
        },
    )
    assert viejo.status_code == 202, viejo.text

    pid = _proyecto(cliente)
    del_borrador = cliente.post(
        f"/proyectos/{pid}/agente/corridas",
        json={
            "restricciones": {
                "energia": "red-electrica",
                "tanque_l": None,
                "presupuesto_bs": None,
            }
        },
    )
    assert del_borrador.status_code == 202, del_borrador.text
    detalle = cliente.get(
        f"/proyectos/{pid}/agente/corridas/{del_borrador.json()['corrida_id']}"
    ).json()
    entrada = detalle["entrada"]
    assert entrada["restricciones"] == {
        "energia": "red-electrica",
        "tanque_l": None,
        "presupuesto_bs": None,
    }
    # Los datos que faltan viajan en null: el agente no los inventa.
    assert entrada["infiltracion_mm_h"] == 12.0
    assert entrada["retencion_agua_mm_m"] is None
    assert entrada["profundidad_nivel_dinamico_m"] is None
    assert entrada["perimetro_m"] == 60.0
    assert [lado["longitud_m"] for lado in entrada["lados_m"]] == [10.0, 20.0, 10.0, 20.0]
    assert len(entrada["geometria"]["vertices"]) == 4
    producto = entrada["productos"][0]
    assert producto["kc"] == 1.15
    assert producto["aptitud_suelo"]["franco"]["veredicto"] == "apto"
    assert producto["profundidad_raiz_cm"] == 40
    assert producto["densidad_plantas_m2"] == 4.0
    assert producto["meses_siembra"] == [3, 4]

    invalida = cliente.post(
        f"/proyectos/{pid}/agente", json={"restricciones": {"energia": "nuclear"}}
    )
    assert invalida.status_code == 422, invalida.text
    cero = cliente.post(f"/proyectos/{pid}/agente", json={"restricciones": {"tanque_l": 0}})
    assert cero.status_code == 422, cero.text
