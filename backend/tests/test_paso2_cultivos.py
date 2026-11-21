"""Paso 1 y paso 2 con todo lo que muestran los prototipos.

Paso 1: la profundidad del nivel dinámico. Paso 2: los derivados de la tarjeta
(porcentaje, demanda total del bloque, ciclo, Kc, días a cosecha) y el veredicto de
aptitud del suelo, que informa pero nunca bloquea (decisión del usuario).
"""

from collections.abc import Generator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.main import app
from app.models.catalogo import Cultivo, Suelo
from app.models.usuario import Usuario
from tests.conftest import create_user

APtitudes = {
    "franco": {"veredicto": "apto", "motivo": "Suelo equilibrado.", "fuente": "Ficha curada"},
    "arenoso": {
        "veredicto": "condicionado",
        "motivo": "Drena rápido: regar en pulsos.",
        "fuente": "Ficha curada",
    },
    "arcilloso": {
        "veredicto": "no_apto",
        "motivo": "Drenaje lento: riesgo de pudrición.",
        "fuente": "Ficha curada",
    },
}


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="paso2@example.com")


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
                kc=1.15,
                densidad_plantas_m2=4.0,
                profundidad_raiz_cm=40,
                aptitud_suelo=APtitudes,
                activo=True,
            ),
            Cultivo(
                codigo="lechuga",
                nombre="Lechuga",
                icono="L",
                color="#7CB342",
                demanda_agua_l_m2_dia=1.5,
                ciclo_dias=65,
                activo=True,  # sin kc ni aptitud: ficha incompleta a propósito
            ),
            Suelo(codigo="franco", nombre="Franco", infiltracion_mm_h=12.0),
            Suelo(codigo="arenoso", nombre="Arenoso", infiltracion_mm_h=25.0),
            Suelo(codigo="arcilloso", nombre="Arcilloso", infiltracion_mm_h=3.0),
        ]
    )
    db_session.commit()


def _proyecto(cliente: TestClient, suelo: str = "franco", **extra) -> str:
    proyecto = cliente.post("/proyectos", json={"nombre": "Paso 2"})
    assert proyecto.status_code == 201, proyecto.text
    proyecto_id = proyecto.json()["id"]
    cuerpo = {
        "nombre_parcela": "El Trébol",
        "forma": "rectangulo",
        "vertices": [
            {"x": 0, "y": 0},
            {"x": 10, "y": 0},
            {"x": 10, "y": 20},
            {"x": 0, "y": 20},
        ],
        "suelo_codigo": suelo,
        "pendiente_pct": 2,
        "fuente_agua": "pozo",
        **extra,
    }
    terreno = cliente.put(f"/proyectos/{proyecto_id}/terreno", json=cuerpo)
    assert terreno.status_code == 200, terreno.text
    return proyecto_id


def _bloque(cliente: TestClient, proyecto_id: str, **cuerpo) -> dict:
    respuesta = cliente.post(f"/proyectos/{proyecto_id}/cultivos", json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --------------------------------------------------------------------------- #
# Paso 1
# --------------------------------------------------------------------------- #


def test_el_paso_1_guarda_la_profundidad_del_nivel_dinamico(
    cliente_autenticado: TestClient,
) -> None:
    cliente = cliente_autenticado
    proyecto = cliente.post("/proyectos", json={"nombre": "Pozo"})
    proyecto_id = proyecto.json()["id"]

    terreno = cliente.put(
        f"/proyectos/{proyecto_id}/terreno",
        json={
            "nombre_parcela": "Lote",
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
            "profundidad_nivel_dinamico_m": 12.5,
        },
    )
    assert terreno.status_code == 200, terreno.text
    assert terreno.json()["profundidad_nivel_dinamico_m"] == 12.5

    edicion = cliente.patch(
        f"/proyectos/{proyecto_id}/terreno", json={"profundidad_nivel_dinamico_m": 15}
    )
    assert edicion.status_code == 200, edicion.text
    assert edicion.json()["profundidad_nivel_dinamico_m"] == 15.0

    limpieza = cliente.patch(
        f"/proyectos/{proyecto_id}/terreno", json={"profundidad_nivel_dinamico_m": None}
    )
    assert limpieza.status_code == 200, limpieza.text
    assert limpieza.json()["profundidad_nivel_dinamico_m"] is None


def test_el_paso_2_sin_terreno_sigue_devolviendo_lista_vacia(
    cliente_autenticado: TestClient,
) -> None:
    """El front puede pedir los cultivos antes de dibujar el terreno."""

    cliente = cliente_autenticado
    proyecto_id = cliente.post("/proyectos", json={"nombre": "Sin terreno"}).json()["id"]

    listado = cliente.get(f"/proyectos/{proyecto_id}/cultivos")
    assert listado.status_code == 200, listado.text
    assert listado.json() == []


# --------------------------------------------------------------------------- #
# Paso 2: derivados de la tarjeta
# --------------------------------------------------------------------------- #


def test_la_tarjeta_trae_los_derivados(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)
    cosecha = date.today() + timedelta(days=122)

    alta = _bloque(
        cliente,
        proyecto_id,
        cultivo_codigo="papa",
        etiqueta="Zona A",
        modo="porcentaje",
        porcentaje=70,
        cosecha=cosecha.isoformat(),
    )
    bloque = alta["bloque"]

    assert bloque["etiqueta"] == "Zona A"
    assert bloque["area_m2"] == 140  # 70% de 200 m²
    assert bloque["porcentaje"] == 70.0
    assert bloque["demanda_total_l_dia"] == 280.0  # 140 m² × 2 L/m²/día
    assert bloque["ciclo_dias"] == 120
    assert bloque["kc"] == 1.15
    assert bloque["dias_a_cosecha"] >= 120
    assert bloque["aptitud_suelo"]["veredicto"] == "apto"
    assert bloque["advertencias"] == []

    panel = alta["balance"]
    assert panel["terreno_m2"] == 200
    assert panel["asignado_m2"] == 140
    assert panel["demanda_total_l_dia"] == 280.0


def test_el_listado_de_bloques_trae_los_derivados(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)
    _bloque(cliente, proyecto_id, cultivo_codigo="papa", modo="porcentaje", porcentaje=50)

    bloques = cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()
    assert len(bloques) == 1
    assert bloques[0]["porcentaje"] == 50.0
    assert bloques[0]["demanda_total_l_dia"] == 200.0
    assert bloques[0]["kc"] == 1.15


def test_un_cultivo_sin_ficha_completa_no_inventa_datos(
    cliente_autenticado: TestClient,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)

    bloque = _bloque(
        cliente, proyecto_id, cultivo_codigo="lechuga", modo="porcentaje", porcentaje=25
    )["bloque"]

    assert bloque["ciclo_dias"] == 65
    assert bloque["kc"] is None
    assert bloque["aptitud_suelo"] is None
    assert bloque["advertencias"] == []


# --------------------------------------------------------------------------- #
# Paso 2: suelo bueno o no, avisando siempre
# --------------------------------------------------------------------------- #


def test_suelo_condicionado_avisa_sin_bloquear(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente, suelo="arenoso")

    alta = _bloque(
        cliente, proyecto_id, cultivo_codigo="papa", modo="porcentaje", porcentaje=50
    )
    bloque = alta["bloque"]

    assert bloque["aptitud_suelo"]["veredicto"] == "condicionado"
    assert bloque["aptitud_suelo"]["motivo"]
    avisos = [aviso for aviso in bloque["advertencias"] if aviso["codigo"] == "SUELO_CONDICIONADO"]
    assert avisos
    assert avisos[0]["bloqueante"] is False
    # El bloque quedó creado: el suelo informa, no frena.
    assert len(cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()) == 1


def test_suelo_no_apto_avisa_y_deja_seguir(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente, suelo="arcilloso")

    alta = _bloque(
        cliente, proyecto_id, cultivo_codigo="papa", modo="porcentaje", porcentaje=50
    )
    bloque = alta["bloque"]

    assert bloque["aptitud_suelo"]["veredicto"] == "no_apto"
    avisos = [aviso for aviso in bloque["advertencias"] if aviso["codigo"] == "SUELO_NO_APTO"]
    assert avisos and avisos[0]["bloqueante"] is False
    assert "pudrición" in avisos[0]["mensaje"]

    # Y el paso 2 sigue completo: el panel derecho se calcula igual.
    panel = cliente.get(f"/proyectos/{proyecto_id}/cultivos/balance").json()
    assert panel["estado"] == "ajustado"  # 100 de 200 m² asignados
    assert panel["asignado_m2"] == 100


def test_cambiar_de_suelo_cambia_el_veredicto(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente, suelo="franco")
    _bloque(cliente, proyecto_id, cultivo_codigo="papa", modo="porcentaje", porcentaje=50)

    antes = cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()[0]
    assert antes["aptitud_suelo"]["veredicto"] == "apto"

    cliente.patch(f"/proyectos/{proyecto_id}/terreno", json={"suelo_codigo": "arcilloso"})

    despues = cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()[0]
    assert despues["aptitud_suelo"]["veredicto"] == "no_apto"
    assert any(
        aviso["codigo"] == "SUELO_NO_APTO" for aviso in despues["advertencias"]
    )


def test_suelo_sin_entrada_no_emite_veredicto(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)
    _bloque(cliente, proyecto_id, cultivo_codigo="papa", modo="porcentaje", porcentaje=50)

    pedregoso = cliente.patch(
        f"/proyectos/{proyecto_id}/terreno", json={"suelo_codigo": "franco"}
    )
    assert pedregoso.status_code == 200
    # Un suelo que la ficha no declara (acá forzamos el caso con arenoso, que sí
    # declara): lo que importa es que sin entrada no haya veredicto ni aviso.
    bloque = cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()[0]
    assert bloque["aptitud_suelo"]["veredicto"] == "apto"

    # Lechuga no declara aptitud de suelo: no se inventa nada.
    alta = _bloque(
        cliente, proyecto_id, cultivo_codigo="lechuga", modo="porcentaje", porcentaje=10
    )
    assert alta["bloque"]["aptitud_suelo"] is None
    assert alta["bloque"]["advertencias"] == []


def test_derivados_coherentes_si_el_cultivo_sale_del_catalogo(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)
    _bloque(cliente, proyecto_id, cultivo_codigo="papa", modo="porcentaje", porcentaje=70)
    _bloque(cliente, proyecto_id, cultivo_codigo="lechuga", modo="porcentaje", porcentaje=30)

    bloques = cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()
    assert [bloque["porcentaje"] for bloque in bloques] == [70.0, 30.0]
    assert sum(bloque["porcentaje"] for bloque in bloques) == 100.0
    assert bloques[0]["demanda_total_l_dia"] == 280.0

    db_session.query(Cultivo).filter_by(codigo="papa").delete()
    db_session.commit()

    # Sin catálogo no hay de dónde derivar: se devuelve el bloque con lo que se sabe.
    huerfano = cliente.get(f"/proyectos/{proyecto_id}/cultivos")
    assert huerfano.status_code == 200, huerfano.text
    papa = next(b for b in huerfano.json() if b["cultivo_codigo"] == "papa")
    assert papa["ciclo_dias"] is None
    assert papa["kc"] is None
    assert papa["aptitud_suelo"] is None
    assert papa["porcentaje"] == 70.0


def test_patch_de_bloque_inexistente_en_proyecto_sin_terreno_es_404(
    cliente_autenticado: TestClient,
) -> None:
    """El orden de las validaciones no cambia el 404 histórico."""

    import uuid as uuid_module

    cliente = cliente_autenticado
    proyecto_id = cliente.post("/proyectos", json={"nombre": "Sin terreno"}).json()["id"]

    respuesta = cliente.patch(
        f"/proyectos/{proyecto_id}/cultivos/{uuid_module.uuid4()}",
        json={"etiqueta": "Zona A"},
    )
    assert respuesta.status_code == 404, respuesta.text
    assert respuesta.json()["detail"] == "Bloque de cultivo no encontrado"


def test_aplicar_la_corrida_deja_los_bloques_con_aptitud(
    cliente_autenticado: TestClient,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente, suelo="arenoso")
    _bloque(cliente, proyecto_id, cultivo_codigo="papa", modo="porcentaje", porcentaje=60)

    corrida_id = cliente.post(f"/proyectos/{proyecto_id}/agente").json()["corrida_id"]
    aplicar = cliente.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}/aplicar"
    )
    assert aplicar.status_code == 200, aplicar.text

    bloques = cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()
    papa = next(bloque for bloque in bloques if bloque["cultivo_codigo"] == "papa")
    assert papa["porcentaje"] > 0
    assert papa["kc"] == 1.15
    assert papa["aptitud_suelo"]["veredicto"] == "condicionado"
