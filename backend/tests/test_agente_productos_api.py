"""Paso 2 nuevo: el usuario elige productos y el agente reparte el área.

Cubre el contrato del disparo con lista de productos (sin bloques previos), la siembra
que viaja al agente, el reparto que cubre todo el terreno y la cosecha derivada.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.main import app
from app.models.catalogo import Cultivo, Suelo
from app.models.usuario import Usuario
from app.schemas.agente import PropuestaAgente
from tests.conftest import create_user


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="reparto@example.com")


@pytest.fixture()
def cliente_autenticado(
    client: TestClient, usuario: Usuario
) -> Generator[TestClient, None, None]:
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
                activo=True,
            ),
            Cultivo(
                codigo="lechuga",
                nombre="Lechuga",
                icono="L",
                color="#7CB342",
                demanda_agua_l_m2_dia=1.5,
                ciclo_dias=65,
                activo=True,
            ),
            Suelo(codigo="franco", nombre="Franco", infiltracion_mm_h=12.0),
        ]
    )
    db_session.commit()


def _proyecto_con_terreno(cliente: TestClient) -> str:
    proyecto = cliente.post("/proyectos", json={"nombre": "Reparto"})
    assert proyecto.status_code == 201, proyecto.text
    proyecto_id = proyecto.json()["id"]

    terreno = cliente.put(
        f"/proyectos/{proyecto_id}/terreno",
        json={
            "nombre_parcela": "El Trébol",
            "forma": "trapecio",
            "vertices": [
                {"x": 0, "y": 40},
                {"x": 60, "y": 40},
                {"x": 60, "y": 20},
                {"x": 30, "y": 0},
                {"x": 0, "y": 0},
            ],
            "suelo_codigo": "franco",
            "pendiente_pct": 1,
            "fuente_agua": "pozo",
            "caudal_disponible_m3h": None,
            "profundidad_nivel_dinamico_m": None,
        },
    )
    assert terreno.status_code == 200, terreno.text
    return proyecto_id


def _corrida(cliente: TestClient, proyecto_id: str, cuerpo: dict) -> dict:
    respuesta = cliente.post(f"/proyectos/{proyecto_id}/agente", json=cuerpo)
    assert respuesta.status_code == 202, respuesta.text
    corrida_id = respuesta.json()["corrida_id"]

    detalle = cliente.get(f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}")
    assert detalle.status_code == 200, detalle.text
    return detalle.json()


def test_el_agente_reparte_el_area_entre_los_productos_elegidos(
    cliente_autenticado: TestClient,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_terreno(cliente)

    detalle = _corrida(
        cliente,
        proyecto_id,
        {
            "productos": [
                {"cultivo_codigo": "papa"},
                {"cultivo_codigo": "lechuga"},
            ],
            "siembra": "2026-11-20",
        },
    )

    assert detalle["estado"] == "ok", detalle["error_detalle"]
    assert detalle["entrada"]["siembra"] == "2026-11-20"
    assert [producto["nombre"] for producto in detalle["entrada"]["productos"]] == [
        "Papa",
        "Lechuga",
    ]

    propuesta = PropuestaAgente.model_validate(detalle["salida"])
    assert len(propuesta.cultivos) == 2
    # El reparto cubre el terreno completo: el cliente no elige porcentajes.
    total = sum(cultivo.area_m2 for cultivo in propuesta.cultivos)
    assert abs(total - detalle["entrada"]["area_m2"]) < 0.5

    for cultivo in propuesta.cultivos:
        assert cultivo.siembra_sugerida is not None
        assert cultivo.siembra_sugerida.isoformat() == "2026-11-20"
        assert cultivo.cosecha_sugerida is not None
        assert cultivo.cosecha_sugerida > cultivo.siembra_sugerida


def test_un_producto_fuera_del_catalogo_se_investiga_al_disparar(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_terreno(cliente)

    detalle = _corrida(
        cliente,
        proyecto_id,
        {"productos": [{"producto_texto": "quinoa"}], "siembra": None},
    )

    assert detalle["estado"] == "ok", detalle["error_detalle"]
    assert [producto["nombre"] for producto in detalle["entrada"]["productos"]] == ["Quinoa"]
    # La ficha curada quedó dada de alta en el catálogo.
    assert db_session.query(Cultivo).filter_by(codigo="quinoa").count() == 1


def test_sin_productos_y_sin_bloques_no_hay_corrida(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_terreno(cliente)

    respuesta = cliente.post(f"/proyectos/{proyecto_id}/agente", json={"productos": []})

    assert respuesta.status_code == 422, respuesta.text
    assert "al menos un cultivo" in respuesta.json()["detail"]


def test_aplicar_deja_los_bloques_con_la_distribucion_del_agente(
    cliente_autenticado: TestClient,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_terreno(cliente)

    inicio = cliente.post(
        f"/proyectos/{proyecto_id}/agente",
        json={
            "productos": [{"cultivo_codigo": "papa"}, {"cultivo_codigo": "lechuga"}],
            "siembra": "2026-11-20",
        },
    )
    corrida_id = inicio.json()["corrida_id"]

    aplicar = cliente.post(f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}/aplicar")
    assert aplicar.status_code == 200, aplicar.text

    bloques = cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()
    assert len(bloques) == 2
    assert abs(sum(bloque["area_m2"] for bloque in bloques) - 2100) < 1
    assert all(bloque["siembra"] == "2026-11-20" for bloque in bloques)

    balance = cliente.get(f"/proyectos/{proyecto_id}/cultivos/balance").json()
    assert balance["estado"] == "correcto"
    assert balance["disponible_m2"] == 0
