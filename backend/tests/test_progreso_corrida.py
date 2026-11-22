"""Progreso visible de la corrida del agente (S1).

La corrida expone en qué fase está y desde cuándo, con las fases que el backend
realmente ejecuta: ``contexto``, ``modelo``, ``validacion``, ``precios``, ``red`` y
``listo``. Ninguna se marca antes de empezar, y si algo falla la corrida queda en
``error`` conservando la fase donde se rompió. El segundo intento del modelo se
publica como sub-fase ``modelo_reintento``, nunca antes: es lo único que se sabe del
modelo mientras la llamada bloquea.
"""

from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agente import ErrorAgente
from app.agente import cliente as agente_cliente
from app.core.config import settings
from app.dependencies import get_current_user
from app.main import app
from app.models.agente import AgenteCorrida
from app.models.catalogo import Cultivo, Suelo
from app.models.usuario import Usuario
from app.repository import agente_corrida as agente_corrida_repo
from app.schemas.agente import (
    CultivoRecomendado,
    EmisorRecomendado,
    PropuestaAgente,
    SistemaRecomendado,
)
from app.services import agente as agente_service
from app.services import riego as riego_service
from tests.conftest import create_user
from tests.test_agente_api import _detalle, _iniciar, _proyecto_con_cultivos


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="progreso@example.com")


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


def _observar_fases(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> list:
    """Registra la fase que quedó guardada en cada commit de la corrida."""

    fases: list[str | None] = []
    original = agente_corrida_repo.update

    def observar(db: Session, corrida: AgenteCorrida) -> AgenteCorrida:
        actualizada = original(db, corrida)
        fases.append(actualizada.fase)
        return actualizada

    monkeypatch.setattr(agente_corrida_repo, "update", observar)
    return fases


def _sin_repetidos(valores: list) -> list:
    return [
        valor
        for indice, valor in enumerate(valores)
        if indice == 0 or valor != valores[indice - 1]
    ]


def _propuesta_cruda() -> dict:
    """Propuesta válida del modelo para un cultivo que existe en el catálogo."""

    return PropuestaAgente(
        cultivos=[
            CultivoRecomendado(
                cultivo_codigo="papa",
                nombre="Papa",
                area_m2=600.0,
                demanda_l_m2_dia=2.0,
                justificacion="Propuesta del modelo.",
            )
        ],
        sistema=SistemaRecomendado(
            tipo="goteo",
            emisor=EmisorRecomendado(tipo="gotero", caudal_lh=2, separacion_m=0.3),
            separacion_laterales_m=0.5,
            bomba_hp=1,
            num_sectores=1,
        ),
    ).model_dump(mode="json")


def _gateway_falso(
    monkeypatch: pytest.MonkeyPatch, respuestas: list[Any]
) -> list[str]:
    """Reemplaza el gateway del modelo y cuenta las llamadas que recibe.

    La primera respuesta se devuelve en el primer intento, la segunda en el segundo y
    así: así se controla qué intento falla y cuál valida.
    """

    llamadas: list[str] = []

    class Respuesta:
        def __init__(self, content: Any) -> None:
            self.content = content

    class Gateway:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def run(self, mensaje: str) -> Respuesta:
            llamadas.append(mensaje)
            return Respuesta(respuestas[min(len(llamadas), len(respuestas)) - 1])

    monkeypatch.setattr(agente_cliente, "_importar_agno", lambda: (Gateway, Gateway))
    monkeypatch.setattr(settings, "AGENTE_MODO", "llm", raising=False)
    monkeypatch.setattr(settings, "AGENTE_API_KEY", "sk-prueba", raising=False)
    return llamadas


# --------------------------------------------------------------------------- #
# El reintento del modelo: la única señal nueva de la fase larga
# --------------------------------------------------------------------------- #


def test_el_reintento_del_modelo_publica_su_sub_fase(
    cliente_autenticado: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    monkeypatch.setattr(settings, "AGENTE_REINTENTOS", 1, raising=False)
    # El primer intento no valida; el segundo sí: la corrida se salva en el reintento.
    llamadas = _gateway_falso(monkeypatch, [{"invalido": True}, _propuesta_cruda()])
    fases = _observar_fases(db_session, monkeypatch)

    inicio = _iniciar(cliente, proyecto_id)
    detalle = _detalle(cliente, proyecto_id, inicio["corrida_id"])

    assert detalle["estado"] == "ok", detalle
    assert len(llamadas) == 2
    assert [fase for fase in _sin_repetidos(fases) if fase is not None] == [
        "contexto",
        "modelo",
        "modelo_reintento",
        "validacion",
        "precios",
        "listo",
    ]


def test_un_solo_intento_no_publica_el_reintento(
    cliente_autenticado: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    # Hay reintentos configurados, pero el primero valida: no se marca la sub-fase.
    monkeypatch.setattr(settings, "AGENTE_REINTENTOS", 2, raising=False)
    llamadas = _gateway_falso(monkeypatch, [_propuesta_cruda()])
    fases = _observar_fases(db_session, monkeypatch)

    inicio = _iniciar(cliente, proyecto_id)
    detalle = _detalle(cliente, proyecto_id, inicio["corrida_id"])

    assert detalle["estado"] == "ok", detalle
    assert len(llamadas) == 1
    assert "modelo_reintento" not in fases


def test_el_detalle_expone_el_presupuesto_de_espera(
    cliente_autenticado: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    monkeypatch.setattr(settings, "AGENTE_TIMEOUT_S", 180, raising=False)

    inicio = _iniciar(cliente, proyecto_id)
    detalle = _detalle(cliente, proyecto_id, inicio["corrida_id"])
    assert detalle["timeout_s"] == 180

    listado = cliente.get(f"/proyectos/{proyecto_id}/agente/corridas")
    assert listado.status_code == 200, listado.text
    assert listado.json()[0]["timeout_s"] == 180


def test_corrida_catalogo_recorre_las_fases_y_termina_listo(
    cliente_autenticado: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    fases = _observar_fases(db_session, monkeypatch)

    inicio = _iniciar(cliente, proyecto_id)
    detalle = _detalle(cliente, proyecto_id, inicio["corrida_id"])

    assert detalle["estado"] == "ok"
    assert detalle["fase"] == "listo"
    assert detalle["fase_desde"] is not None
    assert [fase for fase in _sin_repetidos(fases) if fase is not None] == [
        "contexto",
        "modelo",
        "validacion",
        "precios",
        "listo",
    ]


def test_corrida_que_falla_en_la_validacion_conserva_la_fase(
    cliente_autenticado: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)

    def romper(_db: Session, _entrada, _propuesta):
        raise ValueError("la propuesta no se pudo sanear")

    monkeypatch.setattr(agente_service, "_con_reparto_agronomico", romper)

    inicio = _iniciar(cliente, proyecto_id)
    detalle = _detalle(cliente, proyecto_id, inicio["corrida_id"])

    assert detalle["estado"] == "error"
    assert detalle["fase"] == "validacion"
    assert detalle["fase_desde"] is not None
    assert "la propuesta no se pudo sanear" in detalle["error_detalle"]
    assert detalle["salida"] is None


def test_corrida_que_falla_en_el_modelo_conserva_la_fase_modelo(
    cliente_autenticado: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)

    def fallar(_contexto, on_fase=None):
        raise ErrorAgente("el gateway no respondió")

    monkeypatch.setattr(agente_service, "ejecutar_agente", fallar)

    inicio = _iniciar(cliente, proyecto_id)
    detalle = _detalle(cliente, proyecto_id, inicio["corrida_id"])

    assert detalle["estado"] == "error"
    assert detalle["fase"] == "modelo"
    assert "el gateway no respondió" in detalle["error_detalle"]


def test_corrida_vieja_sin_fases_se_devuelve_sin_romper(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    inicio = _iniciar(cliente, proyecto_id)

    corrida = db_session.query(AgenteCorrida).filter_by().one()
    corrida.fase = None
    corrida.fase_desde = None
    db_session.commit()

    detalle = _detalle(cliente, proyecto_id, inicio["corrida_id"])
    assert detalle["fase"] is None
    assert detalle["fase_desde"] is None

    listado = cliente.get(f"/proyectos/{proyecto_id}/agente/corridas")
    assert listado.status_code == 200, listado.text
    assert listado.json()[0]["fase"] is None


def test_el_detalle_expone_fase_desde_en_iso_con_zona(
    cliente_autenticado: TestClient,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    inicio = _iniciar(cliente, proyecto_id)

    detalle = _detalle(cliente, proyecto_id, inicio["corrida_id"])
    desde = datetime.fromisoformat(detalle["fase_desde"])

    assert desde.tzinfo is not None
    assert desde.utcoffset() is not None
    assert desde <= datetime.now(timezone.utc)


def test_aplicar_que_falla_al_generar_la_red_conserva_la_fase_red(
    cliente_autenticado: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    inicio = _iniciar(cliente, proyecto_id)

    def fallar(_db: Session, _proyecto):
        raise riego_service.RiegoServiceError(409, "la red no entra en el terreno")

    monkeypatch.setattr(riego_service, "generar", fallar)

    respuesta = cliente.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{inicio['corrida_id']}/aplicar"
    )
    assert respuesta.status_code == 409, respuesta.text

    detalle = _detalle(cliente, proyecto_id, inicio["corrida_id"])
    assert detalle["fase"] == "red"
    assert detalle["fase_desde"] is not None


def test_un_timeout_no_se_reintenta_ni_publica_la_sub_fase(
    cliente_autenticado: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La regla de no reintentar un timeout sigue viva: sin segundo intento no hay sub-fase."""

    llamadas: list[str] = []

    class Gateway:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def run(self, mensaje: str) -> Any:
            llamadas.append(mensaje)
            raise TimeoutError("el gateway no contestó")

    monkeypatch.setattr(agente_cliente, "_importar_agno", lambda: (Gateway, Gateway))
    monkeypatch.setattr(settings, "AGENTE_MODO", "llm", raising=False)
    monkeypatch.setattr(settings, "AGENTE_API_KEY", "sk-prueba", raising=False)
    monkeypatch.setattr(settings, "AGENTE_REINTENTOS", 3, raising=False)

    fases = _observar_fases(db_session, monkeypatch)
    proyecto_id = _proyecto_con_cultivos(cliente_autenticado)
    corrida_id = _iniciar(cliente_autenticado, proyecto_id)["corrida_id"]
    detalle = _detalle(cliente_autenticado, proyecto_id, corrida_id)

    assert len(llamadas) == 1
    assert detalle["estado"] == "error"
    assert detalle["fase"] == "modelo"
    assert "modelo_reintento" not in fases


def test_si_el_reintento_tambien_falla_la_fase_guardada_es_la_sub_fase(
    cliente_autenticado: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El error conserva la fase donde se rompió: el mensaje puede decir que reintentaba."""

    llamadas = _gateway_falso(
        monkeypatch, [{"cultivos": "no-es-una-lista"}, {"cultivos": "tampoco"}]
    )
    monkeypatch.setattr(settings, "AGENTE_REINTENTOS", 1, raising=False)

    proyecto_id = _proyecto_con_cultivos(cliente_autenticado)
    corrida_id = _iniciar(cliente_autenticado, proyecto_id)["corrida_id"]
    detalle = _detalle(cliente_autenticado, proyecto_id, corrida_id)

    assert len(llamadas) == 2
    assert detalle["estado"] == "error"
    assert detalle["fase"] == "modelo_reintento"
    assert detalle["error_detalle"]


def test_un_timeout_en_str_no_se_filtra_al_json(
    cliente_autenticado: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``AGENTE_TIMEOUT_S`` fuera de tipo no debe viajar como str al frontend."""

    monkeypatch.setattr(settings, "AGENTE_TIMEOUT_S", "300", raising=False)
    proyecto_id = _proyecto_con_cultivos(cliente_autenticado)
    corrida_id = _iniciar(cliente_autenticado, proyecto_id)["corrida_id"]

    detalle = _detalle(cliente_autenticado, proyecto_id, corrida_id)
    assert detalle["timeout_s"] == 300 and isinstance(detalle["timeout_s"], int)

    listado = cliente_autenticado.get(f"/proyectos/{proyecto_id}/agente/corridas")
    assert listado.status_code == 200, listado.text
    assert listado.json()[0]["timeout_s"] == 300
    assert isinstance(listado.json()[0]["timeout_s"], int)
