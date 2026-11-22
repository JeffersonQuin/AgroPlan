"""Palanca de desarrollo para volver a generar con el mismo intake (pruebas del motor)."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.main import app
from app.models.catalogo import Cultivo, Suelo
from app.models.usuario import Usuario
from tests.conftest import create_user
from tests.test_agente_api import _proyecto_con_cultivos


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="regenerar@example.com")


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


def test_regenerar_fuerza_una_corrida_nueva_con_el_mismo_intake(
    cliente_autenticado: TestClient,
) -> None:
    proyecto_id = _proyecto_con_cultivos(cliente_autenticado)

    primera = cliente_autenticado.post(f"/proyectos/{proyecto_id}/agente", json={})
    assert primera.status_code == 202, primera.text
    reutilizada = cliente_autenticado.post(f"/proyectos/{proyecto_id}/agente", json={})
    assert reutilizada.status_code == 200, reutilizada.text
    assert reutilizada.json()["corrida_id"] == primera.json()["corrida_id"]

    nueva = cliente_autenticado.post(
        f"/proyectos/{proyecto_id}/agente", json={"regenerar": True}
    )

    assert nueva.status_code == 202, nueva.text
    assert nueva.json()["corrida_id"] != primera.json()["corrida_id"]
