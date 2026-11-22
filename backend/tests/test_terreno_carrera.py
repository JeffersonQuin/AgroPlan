"""Paso 1: la carrera de dos guardados simultáneos.

El frontend hace ``PUT`` la primera vez y reintenta como ``PATCH`` cuando la respuesta
es ``409`` (``terrain.store.ts``, rama de error). Esa red de seguridad sólo funciona si
el backend responde 409: si la carrera deja escapar el ``IntegrityError`` del UNIQUE de
``terrenos.proyecto_id``, el cliente recibe un 500 y el guardado se pierde.
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.main import app
from app.models.catalogo import Suelo
from app.models.proyecto import Terreno
from app.models.usuario import Usuario
from app.repository import terreno as terreno_repo
from tests.conftest import create_user

CUERPO = {
    "nombre_parcela": "La Carrera",
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
}


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="carrera@example.com")


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
    db_session.add(Suelo(codigo="franco", nombre="Franco", infiltracion_mm_h=12.0))
    db_session.commit()


def _proyecto(cliente: TestClient) -> str:
    creado = cliente.post("/proyectos", json={"nombre": "Carrera"})
    assert creado.status_code == 201, creado.text
    return creado.json()["id"]


def test_dos_guardados_simultaneos_responden_409_y_no_500(
    db_session: Session,
    cliente_autenticado: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proyecto_id = _proyecto(cliente_autenticado)

    # El primer guardado gana y deja el terreno escrito.
    primero = cliente_autenticado.put(f"/proyectos/{proyecto_id}/terreno", json=CUERPO)
    assert primero.status_code == 200, primero.text

    # El segundo request miró antes de que el primero insertara: ve "sin terreno" y va
    # directo a su INSERT, que choca contra el UNIQUE.
    original = terreno_repo.get_by_proyecto
    miradas: list[Terreno | None] = []

    def mirar_antes_de_que_exista(db: Session, proyecto_id: str) -> Terreno | None:
        visto = None if not miradas else original(db, proyecto_id)
        miradas.append(visto)
        return visto

    monkeypatch.setattr(terreno_repo, "get_by_proyecto", mirar_antes_de_que_exista)

    segundo = cliente_autenticado.put(f"/proyectos/{proyecto_id}/terreno", json=CUERPO)

    assert segundo.status_code == 409, segundo.text
    assert segundo.json()["detail"] == "El proyecto ya tiene terreno; usa PATCH"

    # El 409 sólo se afirma después de ver el terreno de verdad: la mirada previa al
    # INSERT no vio nada y la que sigue al rollback sí encuentra la fila.
    assert len(miradas) == 2, miradas
    assert miradas[0] is None
    assert isinstance(miradas[1], Terreno)

    # El 409 no puede dejar la sesión rota: el reintento como PATCH que hace el
    # frontend tiene que servir sobre la misma conexión.
    assert (
        db_session.query(Terreno)
        .filter_by(proyecto_id=uuid.UUID(proyecto_id))
        .count()
        == 1
    )
    parche = cliente_autenticado.patch(
        f"/proyectos/{proyecto_id}/terreno", json={"pendiente_pct": 4}
    )
    assert parche.status_code == 200, parche.text
    assert parche.json()["pendiente_pct"] == 4.0


def test_un_integrity_error_ajeno_no_se_disfraza_de_409(
    db_session: Session,
    cliente_autenticado: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un fallo que no es la carrera (FK, NOT NULL) no puede responder "ya tiene terreno"."""

    proyecto_id = _proyecto(cliente_autenticado)

    def boom(db: Session, terreno: object) -> None:
        raise IntegrityError("INSERT", {}, Exception("violación ajena a la carrera"))

    monkeypatch.setattr(terreno_repo, "create", boom)

    with pytest.raises(IntegrityError):
        cliente_autenticado.put(f"/proyectos/{proyecto_id}/terreno", json=CUERPO)

    assert (
        db_session.query(Terreno)
        .filter_by(proyecto_id=uuid.UUID(proyecto_id))
        .count()
        == 0
    )
