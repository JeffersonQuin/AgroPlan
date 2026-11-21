"""Flujo completo del wizard a través de la API.

Cubre proyecto, terreno derivado, caudal con procedencia, bloques de cultivo,
balance, configuración de riego, generación de red, resultado y corrida del agente.
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.main import app
from app.models.agente import AgenteRecomendacion
from app.models.catalogo import Cultivo, Suelo
from app.models.enums import TipoRecomendacion
from app.models.usuario import Usuario
from tests.conftest import create_user


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="productor@example.com")


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
            Suelo(
                codigo="franco",
                nombre="Franco",
                infiltracion_mm_h=12.0,
            ),
        ]
    )
    db_session.commit()


def _crear_proyecto(cliente: TestClient) -> dict:
    respuesta = cliente.post(
        "/proyectos", json={"nombre": "Finca Norte", "zona": "Cuyo"}
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


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


def test_flujo_completo_del_wizard(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado

    proyecto = _crear_proyecto(cliente)
    proyecto_id = proyecto["id"]

    listado = cliente.get("/proyectos")
    assert listado.status_code == 200
    assert listado.json()[0]["id"] == proyecto_id

    terreno = _crear_terreno(cliente, proyecto_id)
    assert terreno["area_m2"] == 200
    assert terreno["perimetro_m"] == 60
    assert terreno["lados"] == 4
    assert terreno["caudal_efectivo_m3h"] == 3.0
    assert terreno["caudal_origen"] == "asumido"

    # El caudal del cliente manda y cambia la procedencia.
    edicion = cliente.patch(
        f"/proyectos/{proyecto_id}/terreno",
        json={"caudal_disponible_m3h": 4.5},
    )
    assert edicion.status_code == 200, edicion.text
    assert edicion.json()["caudal_efectivo_m3h"] == 4.5
    assert edicion.json()["caudal_origen"] == "cliente"

    primero = cliente.post(
        f"/proyectos/{proyecto_id}/cultivos",
        json={
            "cultivo_codigo": "papa",
            "modo": "porcentaje",
            "porcentaje": 50,
        },
    )
    assert primero.status_code == 201, primero.text
    assert primero.json()["bloque"]["area_m2"] == 100
    assert primero.json()["balance"]["estado"] == "ajustado"

    segundo = cliente.post(
        f"/proyectos/{proyecto_id}/cultivos",
        json={
            "cultivo_codigo": "lechuga",
            "modo": "porcentaje",
            "porcentaje": 50,
        },
    )
    assert segundo.status_code == 201, segundo.text
    assert segundo.json()["balance"]["estado"] == "correcto"

    balance = cliente.get(f"/proyectos/{proyecto_id}/cultivos/balance")
    assert balance.status_code == 200
    assert balance.json()["asignado_m2"] == 200

    config = cliente.put(
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
    assert config.status_code == 200, config.text
    assert config.json()["emisor"]["caudal_lh"] == 2

    preview = cliente.get(f"/proyectos/{proyecto_id}/riego/preview")
    assert preview.status_code == 200, preview.text
    assert preview.json()["caudal_efectivo_m3h"] == 4.5
    assert preview.json()["computo"]["goteros_u"] > 0

    diseno = cliente.post(f"/proyectos/{proyecto_id}/riego/generar")
    assert diseno.status_code == 200, diseno.text
    cuerpo = diseno.json()
    assert len(cuerpo["sectores"]) == 2
    assert cuerpo["red"]["tramos"]
    assert any(tramo["tipo"] == "lateral" for tramo in cuerpo["red"]["tramos"])
    assert cuerpo["red"]["emisores"]

    guardado = cliente.get(f"/proyectos/{proyecto_id}/riego/diseno")
    assert guardado.status_code == 200
    assert len(guardado.json()["sectores"]) == 2

    resultado = cliente.get(f"/proyectos/{proyecto_id}/resultado")
    assert resultado.status_code == 200, resultado.text
    assert len(resultado.json()["diseno"]["bloques"]) == 2

    corrida = cliente.post(f"/proyectos/{proyecto_id}/agente/corridas")
    assert corrida.status_code == 202, corrida.text
    assert corrida.json()["estado"] == "pendiente"

    corridas = cliente.get(f"/proyectos/{proyecto_id}/agente/corridas")
    assert corridas.status_code == 200
    assert len(corridas.json()) == 1

    detalle = cliente.get(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida.json()['corrida_id']}"
    )
    assert detalle.status_code == 200
    assert detalle.json()["entrada"]["area_m2"] == 200
    # La corrida ya terminó: las fuentes del catálogo quedan persistidas.
    assert [fuente["tipo"] for fuente in detalle.json()["fuentes"]] == [
        "catalogo_interno",
        "catalogo_interno",
    ]

    # Control de concurrencia optimista del autosave.
    desactualizado = cliente.patch(
        f"/proyectos/{proyecto_id}",
        json={"nombre": "Otro nombre", "version": 99},
    )
    assert desactualizado.status_code == 409

    actualizado = cliente.patch(
        f"/proyectos/{proyecto_id}",
        json={"nombre": "Finca Norte 2", "version": 1},
    )
    assert actualizado.status_code == 200, actualizado.text
    assert actualizado.json()["version"] == 2
    assert actualizado.json()["estado"] == "borrador"

    borrado = cliente.delete(f"/proyectos/{proyecto_id}")
    assert borrado.status_code == 204
    assert cliente.get(f"/proyectos/{proyecto_id}").status_code == 404


def test_sectores_explicitos_y_edicion_de_bloque(
    cliente_autenticado: TestClient,
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _crear_proyecto(cliente)["id"]
    _crear_terreno(cliente, proyecto_id)

    papa = cliente.post(
        f"/proyectos/{proyecto_id}/cultivos",
        json={"cultivo_codigo": "papa", "modo": "porcentaje", "porcentaje": 50},
    ).json()["bloque"]
    lechuga = cliente.post(
        f"/proyectos/{proyecto_id}/cultivos",
        json={"cultivo_codigo": "lechuga", "modo": "porcentaje", "porcentaje": 50},
    ).json()["bloque"]

    edicion = cliente.patch(
        f"/proyectos/{proyecto_id}/cultivos/{papa['id']}",
        json={"etiqueta": "Papa norte"},
    )
    assert edicion.status_code == 200, edicion.text
    assert edicion.json()["bloque"]["etiqueta"] == "Papa norte"

    config = cliente.put(
        f"/proyectos/{proyecto_id}/riego",
        json={
            "tipo": "goteo",
            "fuente_agua": "pozo",
            "bomba_hp": 1,
            "diametro_principal_mm": 32,
            "emisor": {"tipo": "gotero", "caudal_lh": 4, "separacion_m": 0.4},
            "separacion_laterales_m": 4,
            "orientacion": "N-S",
            "punto_conexion": {"x": 0, "y": 0},
            "num_sectores": 2,
        },
    )
    assert config.status_code == 200, config.text

    respuesta = cliente.put(
        f"/proyectos/{proyecto_id}/riego/sectores",
        json={
            "sectores": [
                {
                    "numero": 1,
                    "etiqueta": "Turno mañana",
                    "cultivo_ids": [papa["id"]],
                    "area_m2": 100,
                    "secuencia": 1,
                },
                {
                    "numero": 2,
                    "etiqueta": "Turno tarde",
                    "cultivo_ids": [lechuga["id"]],
                    "area_m2": 100,
                    "secuencia": 2,
                },
            ]
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert len(cuerpo["sectores"]) == 2
    assert cuerpo["sectores"][0]["etiqueta"] == "Turno mañana"
    assert cuerpo["sectores"][0]["cultivo_ids"] == [papa["id"]]
    assert cuerpo["computo"]["valvulas_u"] == 2


def test_proyecto_ajeno_no_es_visible(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    proyecto = _crear_proyecto(cliente_autenticado)
    otro = create_user(db_session, email="otro@example.com")

    app.dependency_overrides[get_current_user] = lambda: otro
    try:
        respuesta = cliente_autenticado.get(f"/proyectos/{proyecto['id']}")
        assert respuesta.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_catalogos_publicos(cliente_autenticado: TestClient) -> None:
    cultivos = cliente_autenticado.get("/catalogos/cultivos")
    suelos = cliente_autenticado.get("/catalogos/suelos")
    assert cultivos.status_code == 200
    assert {cultivo["codigo"] for cultivo in cultivos.json()} == {"papa", "lechuga"}
    assert suelos.status_code == 200
    assert suelos.json()[0]["codigo"] == "franco"


def test_endpoints_por_tabla_de_riego_y_agente(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _crear_proyecto(cliente)["id"]
    _crear_terreno(cliente, proyecto_id)

    def crear_bloque(codigo: str, porcentaje: int) -> dict:
        respuesta = cliente.post(
            f"/proyectos/{proyecto_id}/cultivos",
            json={
                "cultivo_codigo": codigo,
                "modo": "porcentaje",
                "porcentaje": porcentaje,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()["bloque"]

    papa = crear_bloque("papa", 30)
    lechuga = crear_bloque("lechuga", 30)
    extra = crear_bloque("papa", 40)

    config = cliente.put(
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
    assert config.status_code == 200, config.text

    aplicado = cliente.put(
        f"/proyectos/{proyecto_id}/riego/sectores",
        json={
            "sectores": [
                {
                    "numero": 1,
                    "etiqueta": "Sector papa",
                    "cultivo_ids": [papa["id"]],
                    "area_m2": 60,
                    "secuencia": 1,
                },
                {
                    "numero": 2,
                    "etiqueta": "Sector lechuga",
                    "cultivo_ids": [lechuga["id"]],
                    "area_m2": 60,
                    "secuencia": 2,
                },
            ]
        },
    )
    assert aplicado.status_code == 200, aplicado.text
    sector_papa, sector_lechuga = aplicado.json()["sectores"]
    assert sector_papa["cultivo_ids"] == [papa["id"]]

    # Router de sectores.
    listado = cliente.get(f"/proyectos/{proyecto_id}/riego/sectores")
    assert listado.status_code == 200, listado.text
    assert len(listado.json()) == 2

    detalle = cliente.get(
        f"/proyectos/{proyecto_id}/riego/sectores/{sector_papa['id']}"
    )
    assert detalle.status_code == 200
    assert detalle.json()["numero"] == 1

    editado = cliente.patch(
        f"/proyectos/{proyecto_id}/riego/sectores/{sector_papa['id']}",
        json={"etiqueta": "Sector papa norte", "secuencia": 3},
    )
    assert editado.status_code == 200, editado.text
    assert editado.json()["etiqueta"] == "Sector papa norte"
    assert editado.json()["secuencia"] == 3

    # Router de sector_bloques.
    vinculos = cliente.get(
        f"/proyectos/{proyecto_id}/riego/sectores/{sector_lechuga['id']}/bloques"
    )
    assert vinculos.status_code == 200, vinculos.text
    assert len(vinculos.json()) == 1
    vinculo = vinculos.json()[0]
    assert vinculo["proyecto_cultivo_id"] == lechuga["id"]

    detalle_vinculo = cliente.get(
        f"/proyectos/{proyecto_id}/riego/sectores/"
        f"{sector_lechuga['id']}/bloques/{vinculo['id']}"
    )
    assert detalle_vinculo.status_code == 200

    nuevo = cliente.post(
        f"/proyectos/{proyecto_id}/riego/sectores/"
        f"{sector_lechuga['id']}/bloques",
        json={"proyecto_cultivo_id": extra["id"], "area_m2": 80},
    )
    assert nuevo.status_code == 201, nuevo.text
    assert nuevo.json()["proyecto_cultivo_id"] == extra["id"]

    recalculado = cliente.get(
        f"/proyectos/{proyecto_id}/riego/sectores/{sector_lechuga['id']}"
    )
    assert recalculado.status_code == 200
    assert recalculado.json()["area_m2"] == 140

    borrado = cliente.delete(
        f"/proyectos/{proyecto_id}/riego/sectores/"
        f"{sector_lechuga['id']}/bloques/{nuevo.json()['id']}"
    )
    assert borrado.status_code == 204

    # Routers de red_tramos y red_nodos.
    tramos = cliente.get(f"/proyectos/{proyecto_id}/riego/tramos")
    assert tramos.status_code == 200, tramos.text
    assert tramos.json()
    assert any(tramo["tipo"] == "lateral" for tramo in tramos.json())
    tramo = tramos.json()[0]
    assert (
        cliente.get(
            f"/proyectos/{proyecto_id}/riego/tramos/{tramo['id']}"
        ).status_code
        == 200
    )

    nodos = cliente.get(f"/proyectos/{proyecto_id}/riego/nodos")
    assert nodos.status_code == 200, nodos.text
    assert nodos.json()
    nodo = nodos.json()[0]
    assert (
        cliente.get(
            f"/proyectos/{proyecto_id}/riego/nodos/{nodo['id']}"
        ).status_code
        == 200
    )

    # Routers de agente_corrida, agente_fuente y agente_recomendacion.
    corrida = cliente.post(f"/proyectos/{proyecto_id}/agente/corridas")
    assert corrida.status_code == 202, corrida.text
    corrida_id = corrida.json()["corrida_id"]

    fuentes = cliente.get(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}/fuentes"
    )
    assert fuentes.status_code == 200
    assert [fuente["tipo"] for fuente in fuentes.json()] == [
        "catalogo_interno",
        "catalogo_interno",
    ]

    recomendaciones = cliente.get(
        f"/proyectos/{proyecto_id}/agente/corridas/"
        f"{corrida_id}/recomendaciones"
    )
    assert recomendaciones.status_code == 200
    tipos = [fila["tipo"] for fila in recomendaciones.json()]
    assert "sistema_riego" in tipos
    assert "advertencia" in tipos
    assert all(not fila["aplicada"] for fila in recomendaciones.json())

    recomendacion = AgenteRecomendacion(
        corrida_id=uuid.UUID(corrida_id),
        tipo=TipoRecomendacion.ADVERTENCIA.value,
        payload={"codigo": "revisar_caudal"},
        justificacion="Verifica el caudal real antes de regar.",
        aplicada=False,
    )
    db_session.add(recomendacion)
    db_session.commit()
    db_session.refresh(recomendacion)

    aplicada = cliente.patch(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}/"
        f"recomendaciones/{recomendacion.id}",
        json={"aplicada": True},
    )
    assert aplicada.status_code == 200, aplicada.text
    assert aplicada.json()["aplicada"] is True
    assert aplicada.json()["aplicada_en"] is not None

    # Routers de catálogo por tabla.
    assert cliente.get("/catalogos/cultivos/papa").status_code == 200
    assert cliente.get("/catalogos/suelos/franco").status_code == 200
    assert cliente.get("/catalogos/cultivos/inexistente").status_code == 404
    assert cliente.get("/catalogos/suelos/inexistente").status_code == 404
