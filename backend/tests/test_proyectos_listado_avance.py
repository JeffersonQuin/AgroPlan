"""Avance derivado y datos de la tarjeta en ``GET /proyectos``.

El paso del listado se deriva de las tablas (terreno → cultivos → riego → corrida
del agente terminada en ok), nunca de la columna ``ultimo_paso_completado``, que
solo escribe un PATCH y por eso dejaba todas las tarjetas en "Paso 1".
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
from app.models.enums import EstadoCorrida
from app.models.usuario import Usuario
from tests.conftest import create_user


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="tarjeta@example.com")


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
            Suelo(
                codigo="franco",
                nombre="Franco",
                infiltracion_mm_h=12.0,
            ),
        ]
    )
    db_session.commit()


def _crear_proyecto(cliente: TestClient) -> str:
    respuesta = cliente.post(
        "/proyectos", json={"nombre": "Finca Norte", "zona": "Cuyo"}
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _crear_terreno(cliente: TestClient, proyecto_id: str) -> dict:
    respuesta = cliente.put(
        f"/proyectos/{proyecto_id}/terreno",
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
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _crear_cultivo(cliente: TestClient, proyecto_id: str) -> dict:
    respuesta = cliente.post(
        f"/proyectos/{proyecto_id}/cultivos",
        json={"cultivo_codigo": "papa", "modo": "porcentaje", "porcentaje": 100},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["bloque"]


def _crear_sistema_riego(cliente: TestClient, proyecto_id: str) -> dict:
    respuesta = cliente.put(
        f"/proyectos/{proyecto_id}/riego",
        json={
            "tipo": "goteo",
            "fuente_agua": "pozo",
            "bomba_hp": 1,
            "diametro_principal_mm": 32,
            "emisor": {"tipo": "gotero", "caudal_lh": 2, "separacion_m": 0.3},
            "separacion_laterales_m": 5,
            "orientacion": "E-O",
            "punto_conexion": {"x": 0, "y": 0},
            "num_sectores": 2,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _tarjeta(cliente: TestClient, proyecto_id: str) -> dict:
    respuesta = cliente.get("/proyectos")
    assert respuesta.status_code == 200, respuesta.text
    tarjetas = [fila for fila in respuesta.json() if fila["id"] == proyecto_id]
    assert len(tarjetas) == 1, respuesta.json()
    return tarjetas[0]


# --------------------------------------------------------------------------- #
# Avance derivado (S5)
# --------------------------------------------------------------------------- #


def test_proyecto_sin_terreno_queda_en_paso_1_sin_datos_de_terreno(
    cliente_autenticado: TestClient,
) -> None:
    proyecto_id = _crear_proyecto(cliente_autenticado)

    tarjeta = _tarjeta(cliente_autenticado, proyecto_id)

    assert tarjeta["ultimo_paso_completado"] == 1
    assert tarjeta["estado"] != "completado"
    assert tarjeta["area_m2"] is None
    assert tarjeta["pendiente_pct"] is None
    assert tarjeta["geometria"] is None
    assert tarjeta["num_sectores"] is None
    assert tarjeta["cultivos_count"] == 0
    assert tarjeta["sistema_tipo"] is None


def test_con_terreno_expone_area_pendiente_y_geometria(
    cliente_autenticado: TestClient,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _crear_proyecto(cliente)
    terreno = _crear_terreno(cliente, proyecto_id)

    tarjeta = _tarjeta(cliente, proyecto_id)

    # Con terreno guardado pero sin cultivos, el avance sigue en el paso 1.
    assert tarjeta["ultimo_paso_completado"] == 1
    assert tarjeta["estado"] != "completado"
    assert tarjeta["area_m2"] == 200
    assert tarjeta["pendiente_pct"] == 2
    assert tarjeta["geometria"]["cerrado"] is True
    assert tarjeta["geometria"]["unidad"] == "m"
    assert tarjeta["geometria"]["vertices"] == terreno["geometria"]["vertices"]
    assert len(tarjeta["geometria"]["vertices"]) == 4
    assert tarjeta["num_sectores"] is None


def test_con_un_cultivo_sube_al_paso_2(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _crear_proyecto(cliente)
    _crear_terreno(cliente, proyecto_id)
    _crear_cultivo(cliente, proyecto_id)

    tarjeta = _tarjeta(cliente, proyecto_id)

    assert tarjeta["cultivos_count"] == 1
    assert tarjeta["ultimo_paso_completado"] == 2
    assert tarjeta["estado"] != "completado"


def test_con_sistema_de_riego_sube_al_paso_3_y_expone_sus_sectores(
    cliente_autenticado: TestClient,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _crear_proyecto(cliente)
    _crear_terreno(cliente, proyecto_id)
    _crear_cultivo(cliente, proyecto_id)
    _crear_sistema_riego(cliente, proyecto_id)

    tarjeta = _tarjeta(cliente, proyecto_id)

    assert tarjeta["sistema_tipo"] == "goteo"
    assert tarjeta["num_sectores"] == 2
    assert tarjeta["ultimo_paso_completado"] == 3
    assert tarjeta["estado"] != "completado"


def test_con_corrida_terminada_en_ok_sube_al_paso_4_y_completa(
    cliente_autenticado: TestClient,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _crear_proyecto(cliente)
    _crear_terreno(cliente, proyecto_id)
    _crear_cultivo(cliente, proyecto_id)
    _crear_sistema_riego(cliente, proyecto_id)

    corrida = cliente.post(f"/proyectos/{proyecto_id}/agente/corridas")
    assert corrida.status_code == 202, corrida.text
    detalle = cliente.get(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida.json()['corrida_id']}"
    )
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["estado"] == "ok"

    tarjeta = _tarjeta(cliente, proyecto_id)

    assert tarjeta["ultimo_paso_completado"] == 4
    assert tarjeta["estado"] == "completado"


def test_corrida_en_error_no_cuenta_como_paso_4(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _crear_proyecto(cliente)
    _crear_terreno(cliente, proyecto_id)
    _crear_cultivo(cliente, proyecto_id)
    _crear_sistema_riego(cliente, proyecto_id)

    corrida = cliente.post(f"/proyectos/{proyecto_id}/agente/corridas")
    assert corrida.status_code == 202, corrida.text
    fila = db_session.get(AgenteCorrida, uuid.UUID(corrida.json()["corrida_id"]))
    fila.estado = EstadoCorrida.ERROR.value
    fila.salida = None
    fila.error_detalle = "El gateway no respondió"
    db_session.commit()

    tarjeta = _tarjeta(cliente, proyecto_id)

    assert tarjeta["ultimo_paso_completado"] == 3
    assert tarjeta["estado"] != "completado"


# --------------------------------------------------------------------------- #
# PRESERVE: lo que el listado ya devolvía sigue igual
# --------------------------------------------------------------------------- #


def test_el_listado_conserva_los_campos_que_ya_consumia_el_frontend(
    cliente_autenticado: TestClient,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _crear_proyecto(cliente)
    _crear_terreno(cliente, proyecto_id)

    tarjeta = _tarjeta(cliente, proyecto_id)

    assert tarjeta["id"] == proyecto_id
    assert tarjeta["nombre"] == "Finca Norte"
    assert tarjeta["zona"] == "Cuyo"
    assert tarjeta["unidad"] == "metric"
    assert tarjeta["version"] == 1
    assert tarjeta["actualizado_en"]
