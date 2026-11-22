"""Imágenes híbridas del paso 4 (T3, S4).

Cubre que la imagen de la ficha curada viaje en la entrada del agente y en el prompt,
que el catálogo exponga la columna nueva y que el agente no tenga que investigar una
imagen que ya existe. Las URLs reales de las fichas llegan en otro corte: acá se usan
valores de prueba.
"""

import json
import uuid
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agente import fichas as fichas_agente
from app.agente.instrucciones import construir_mensaje
from app.dependencies import get_current_user
from app.main import app
from app.models.agente import AgenteCorrida
from app.models.catalogo import Cultivo, Suelo
from app.models.proyecto import Proyecto
from app.models.usuario import Usuario
from app.schemas.agente import EntradaAgente
from app.services import agente as agente_service
from tests.conftest import create_user

IMAGEN_FICHA = "https://fichas.example/papa.jpg"
FUENTE_FICHA = "https://fichas.example/papa"
CREDITO_FICHA = "Foto: Scott Bauer, USDA ARS / Wikimedia Commons, dominio público"
IMAGEN_CATALOGO = "https://catalogo.example/papa.jpg"


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="imagenes4@example.com")


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
                activo=True,
            ),
            Suelo(codigo="franco", nombre="Franco", infiltracion_mm_h=12.0),
        ]
    )
    db_session.commit()


def _escribir_ficha(
    directorio: Path,
    *,
    codigo: str = "papa",
    imagen: str | None = IMAGEN_FICHA,
    imagen_fuente: str | None = FUENTE_FICHA,
    imagen_credito: str | None = CREDITO_FICHA,
) -> None:
    datos = {
        "codigo": codigo,
        "nombre": "Papa",
        "icono": "P",
        "color": "#8D6E63",
        "demanda_agua_l_m2_dia": 2.0,
        "ciclo_dias": 120,
        "meses_siembra": [3, 4, 9, 10],
        "notas": "Ficha de prueba.",
        "fuentes": [
            {
                "tipo": "manual",
                "titulo": "Ficha técnica curada AgroPlan",
                "url": None,
                "fragmento": "Demanda y ciclo del catálogo base",
            }
        ],
        "imagen": imagen,
        "imagen_fuente": imagen_fuente,
        "imagen_credito": imagen_credito,
    }
    (directorio / f"{codigo}.json").write_text(
        json.dumps(datos, ensure_ascii=False), encoding="utf-8"
    )


@pytest.fixture()
def fichas_temporales(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _escribir_ficha(tmp_path)
    monkeypatch.setattr(fichas_agente, "DIRECTORIO_FICHAS", tmp_path)
    fichas_agente._cargar.cache_clear()
    try:
        yield tmp_path
    finally:
        fichas_agente._cargar.cache_clear()


def _proyecto_con_papa(cliente: TestClient) -> str:
    proyecto = cliente.post("/proyectos", json={"nombre": "Finca T3", "zona": "Cuyo"})
    assert proyecto.status_code == 201, proyecto.text
    proyecto_id = proyecto.json()["id"]

    terreno = cliente.put(
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
    assert terreno.status_code == 200, terreno.text

    bloque = cliente.post(
        f"/proyectos/{proyecto_id}/cultivos",
        json={"cultivo_codigo": "papa", "modo": "porcentaje", "porcentaje": 100},
    )
    assert bloque.status_code == 201, bloque.text
    return proyecto_id


def test_el_cargador_lee_la_imagen_y_su_fuente(fichas_temporales: Path) -> None:
    ficha = fichas_agente.buscar("papa")

    assert ficha is not None
    assert ficha.imagen == IMAGEN_FICHA
    assert ficha.imagen_fuente == FUENTE_FICHA
    assert ficha.imagen_credito == CREDITO_FICHA


def test_las_fichas_reales_traen_imagen_y_credito() -> None:
    """Protege contra un JSON roto o una foto sin su atribución obligatoria."""

    fichas_agente._cargar.cache_clear()
    try:
        lista = fichas_agente.listar()
    finally:
        fichas_agente._cargar.cache_clear()

    assert len(lista) == 15
    for ficha in lista:
        assert ficha.imagen is not None, ficha.codigo
        partes = urlparse(ficha.imagen)
        assert partes.scheme in ("http", "https") and partes.netloc, ficha.codigo
        assert ficha.imagen_credito and ficha.imagen_credito.strip(), ficha.codigo


def test_la_imagen_de_la_ficha_llega_a_la_entrada_y_al_prompt(
    cliente_autenticado: TestClient,
    db_session: Session,
    fichas_temporales: Path,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_papa(cliente)
    proyecto = db_session.get(Proyecto, uuid.UUID(proyecto_id))
    assert proyecto is not None

    inicio = agente_service.iniciar_corrida(db_session, proyecto)
    corrida = db_session.get(AgenteCorrida, inicio.corrida_id)
    assert corrida is not None
    entrada = EntradaAgente.model_validate(corrida.entrada)

    producto = entrada.productos[0]
    assert producto.cultivo_codigo == "papa"
    assert producto.imagen_url == IMAGEN_FICHA

    mensaje = construir_mensaje(
        entrada,
        catalogo=[{"codigo": "papa", "nombre": "Papa"}],
        suelo=None,
        riego_actual=None,
        bloques=1,
    )
    assert IMAGEN_FICHA in mensaje
    # La regla del prompt tiene que decir explícitamente que no se investigue otra.
    assert "no investigues otra" in mensaje


def test_la_imagen_del_catalogo_manda_sobre_la_ficha(
    cliente_autenticado: TestClient,
    db_session: Session,
    fichas_temporales: Path,
) -> None:
    cliente = cliente_autenticado
    cultivo = db_session.get(Cultivo, "papa")
    assert cultivo is not None
    cultivo.imagen_url = IMAGEN_CATALOGO
    db_session.commit()

    proyecto_id = _proyecto_con_papa(cliente)
    proyecto = db_session.get(Proyecto, uuid.UUID(proyecto_id))
    assert proyecto is not None

    inicio = agente_service.iniciar_corrida(db_session, proyecto)
    corrida = db_session.get(AgenteCorrida, inicio.corrida_id)
    assert corrida is not None
    entrada = EntradaAgente.model_validate(corrida.entrada)

    assert entrada.productos[0].imagen_url == IMAGEN_CATALOGO


def test_el_catalogo_expone_la_imagen_del_cultivo(
    client: TestClient, db_session: Session
) -> None:
    cultivo = db_session.get(Cultivo, "papa")
    assert cultivo is not None
    cultivo.imagen_url = IMAGEN_CATALOGO
    cultivo.imagen_credito = CREDITO_FICHA
    db_session.commit()

    respuesta = client.get("/catalogos/cultivos")
    assert respuesta.status_code == 200, respuesta.text
    papa = next(
        item for item in respuesta.json() if item["codigo"] == "papa"
    )
    assert papa["imagen_url"] == IMAGEN_CATALOGO
    assert papa["imagen_credito"] == CREDITO_FICHA


def test_un_cultivo_nuevo_desde_ficha_curada_hereda_la_imagen(
    cliente_autenticado: TestClient,
) -> None:
    """S4: dar de alta un producto que tiene ficha curada no puede perder la foto."""
    proyecto = cliente_autenticado.post("/proyectos", json={"nombre": "P", "zona": "Cuyo"})
    pid = proyecto.json()["id"]
    assert cliente_autenticado.put(
        f"/proyectos/{pid}/terreno",
        json={
            "nombre_parcela": "L1",
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
    ).status_code == 200

    bloque = cliente_autenticado.post(
        f"/proyectos/{pid}/cultivos", json={"producto_texto": "arroz", "porcentaje": 100}
    )
    assert bloque.status_code == 201, bloque.text

    catalogo = cliente_autenticado.get("/catalogos/cultivos").json()
    arroz = next(cultivo for cultivo in catalogo if cultivo["codigo"] == "arroz")
    assert arroz["imagen_url"].startswith("https://upload.wikimedia.org/")
    assert arroz["imagen_credito"]
