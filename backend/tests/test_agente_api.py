"""Contrato y flujo del agente de recomendaciones.

Cubre S2 (la IA no escribe ni calcula geometría; el backend valida antes de aplicar),
S3 (202 + tarea de fondo, estados, idempotencia por intake, ``aplicar``) y S4 (las
observaciones de la revisión: snapshot, hash del intake real, fuentes reales,
correcciones, reparto sin exceder el terreno).
"""

import uuid
from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agente import ErrorAgente
from app.agente.validacion import (
    PropuestaInvalida,
    corregir,
    repartir_porcentajes,
)
from app.dependencies import get_current_user
from app.main import app
from app.models.agente import AgenteRecomendacion
from app.models.catalogo import Cultivo, Suelo
from app.models.proyecto import Proyecto
from app.models.usuario import Usuario
from app.schemas.agente import (
    CultivoRecomendado,
    EmisorRecomendado,
    EntradaAgente,
    ProductoDeseado,
    PropuestaAgente,
    SistemaRecomendado,
)
from app.services import agente as agente_service
from tests.conftest import create_user

AREA_TERRENO = 200

CATALOGO = {
    "papa": {"nombre": "Papa", "color": "#8D6E63", "demanda": 2.0, "ciclo": 120},
    "lechuga": {"nombre": "Lechuga", "color": "#7CB342", "demanda": 1.5, "ciclo": 65},
}


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="agente@example.com")


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


def _proyecto_con_cultivos(cliente: TestClient) -> str:
    proyecto = cliente.post("/proyectos", json={"nombre": "Finca Agente", "zona": "Cuyo"})
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

    for codigo in ("papa", "lechuga"):
        bloque = cliente.post(
            f"/proyectos/{proyecto_id}/cultivos",
            json={"cultivo_codigo": codigo, "modo": "porcentaje", "porcentaje": 50},
        )
        assert bloque.status_code == 201, bloque.text
    return proyecto_id


def _iniciar(cliente: TestClient, proyecto_id: str) -> dict:
    respuesta = cliente.post(f"/proyectos/{proyecto_id}/agente")
    assert respuesta.status_code == 202, respuesta.text
    return respuesta.json()


def _detalle(cliente: TestClient, proyecto_id: str, corrida_id: str) -> dict:
    respuesta = cliente.get(f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# --------------------------------------------------------------------------- #
# S3 — la corrida se crea y se cierra por la API
# --------------------------------------------------------------------------- #


def test_corrida_termina_ok_y_congela_el_snapshot(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)

    inicio = _iniciar(cliente, proyecto_id)
    assert inicio["estado"] == "pendiente"
    assert len(inicio["intake_hash"]) == 64

    detalle = _detalle(cliente, proyecto_id, inicio["corrida_id"])
    assert detalle["estado"] == "ok", detalle
    assert detalle["modelo"] == "catalogo"
    assert detalle["duracion_ms"] is not None
    assert detalle["terminado_en"] is not None
    assert detalle["error_detalle"] is None
    assert detalle["prompt_version"] == "v4"
    assert detalle["motor_version"]

    propuesta = PropuestaAgente.model_validate(detalle["salida"])
    assert propuesta.cultivos
    # El fallback no inventa cultivos que el usuario no pidió.
    assert len(propuesta.cultivos) <= 2
    assert sum(cultivo.area_m2 for cultivo in propuesta.cultivos) <= AREA_TERRENO
    for cultivo in propuesta.cultivos:
        assert cultivo.cultivo_codigo in CATALOGO
        assert cultivo.color == CATALOGO[cultivo.cultivo_codigo]["color"]

    # Las fuentes son reales y los índices citados existen en esa lista.
    assert len(detalle["fuentes"]) == 2
    for fuente in detalle["fuentes"]:
        assert fuente["tipo"] == "catalogo_interno"
        assert fuente["tipo"] in {"web", "catalogo_interno", "norma", "manual"}
    for cultivo in propuesta.cultivos:
        assert cultivo.fuente_ids
        assert max(cultivo.fuente_ids) <= len(detalle["fuentes"])

    # El snapshot del intake es el del backend, no el de la salida del modelo.
    assert detalle["entrada"]["area_m2"] == AREA_TERRENO
    assert detalle["entrada"]["productos"][0]["nombre"] == "Papa"


def test_la_corrida_no_escribe_en_el_proyecto(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    antes = cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()

    inicio = _iniciar(cliente, proyecto_id)
    _detalle(cliente, proyecto_id, inicio["corrida_id"])

    despues = cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()
    assert [bloque["id"] for bloque in despues] == [bloque["id"] for bloque in antes]
    assert cliente.get(f"/proyectos/{proyecto_id}/riego").status_code == 404

    recomendaciones = cliente.get(
        f"/proyectos/{proyecto_id}/agente/corridas/{inicio['corrida_id']}/recomendaciones"
    )
    assert recomendaciones.status_code == 200, recomendaciones.text
    assert recomendaciones.json()
    assert all(not fila["aplicada"] for fila in recomendaciones.json())


def test_mismo_intake_reutiliza_la_corrida(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)

    primera = _iniciar(cliente, proyecto_id)
    segunda = cliente.post(f"/proyectos/{proyecto_id}/agente")

    assert segunda.status_code == 200, segunda.text
    assert segunda.json()["corrida_id"] == primera["corrida_id"]
    assert segunda.json()["intake_hash"] == primera["intake_hash"]
    assert len(cliente.get(f"/proyectos/{proyecto_id}/agente/corridas").json()) == 1


def test_corrida_en_curso_responde_409(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)

    proyecto = db_session.get(Proyecto, uuid.UUID(proyecto_id))
    assert proyecto is not None
    agente_service.iniciar_corrida(db_session, proyecto)

    respuesta = cliente.post(f"/proyectos/{proyecto_id}/agente")
    assert respuesta.status_code == 409, respuesta.text


def test_sin_cultivos_no_hay_corrida(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto = cliente.post("/proyectos", json={"nombre": "Sin cultivos"})
    proyecto_id = proyecto.json()["id"]
    cliente.put(
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
        },
    )

    respuesta = cliente.post(f"/proyectos/{proyecto_id}/agente")
    assert respuesta.status_code == 422, respuesta.text


def test_corrida_error_registra_el_detalle(
    cliente_autenticado: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)

    def fallar(_contexto):
        raise ErrorAgente("el gateway no respondió")

    monkeypatch.setattr(agente_service, "ejecutar_agente", fallar)

    inicio = _iniciar(cliente, proyecto_id)
    detalle = _detalle(cliente, proyecto_id, inicio["corrida_id"])
    assert detalle["estado"] == "error"
    assert "el gateway no respondió" in detalle["error_detalle"]
    assert detalle["salida"] is None


def test_producto_no_reconocido_no_se_reemplaza_en_silencio(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    """Si el catálogo pierde un cultivo ya asignado, el agente lo dice."""

    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)

    lechuga = db_session.query(Cultivo).filter_by(codigo="lechuga").one()
    lechuga.activo = False
    db_session.commit()

    inicio = _iniciar(cliente, proyecto_id)
    salida = _detalle(cliente, proyecto_id, inicio["corrida_id"])["salida"]

    codigos = [alerta["codigo"] for alerta in salida["advertencias"]]
    assert "PRODUCTO_NO_RECONOCIDO" in codigos
    assert all(
        cultivo["cultivo_codigo"] != "lechuga" for cultivo in salida["cultivos"]
    )


# --------------------------------------------------------------------------- #
# S2 / S3 — aplicar es el único paso que escribe
# --------------------------------------------------------------------------- #


def test_aplicar_materializa_bloques_y_riego(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    inicio = _iniciar(cliente, proyecto_id)
    salida = _detalle(cliente, proyecto_id, inicio["corrida_id"])["salida"]

    respuesta = cliente.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{inicio['corrida_id']}/aplicar"
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert len(cuerpo["diseno"]["bloques"]) == len(salida["cultivos"])
    total = sum(bloque["area_m2"] for bloque in cuerpo["diseno"]["bloques"])
    assert abs(total - AREA_TERRENO) < 1.0
    assert cuerpo["diseno"]["sectores"]
    assert cuerpo["diseno"]["red"]["tramos"]

    balance = cliente.get(f"/proyectos/{proyecto_id}/cultivos/balance").json()
    assert balance["estado"] == "correcto"
    assert balance["asignado_m2"] <= AREA_TERRENO

    recomendaciones = cliente.get(
        f"/proyectos/{proyecto_id}/agente/corridas/{inicio['corrida_id']}/recomendaciones"
    ).json()
    assert all(fila["aplicada"] for fila in recomendaciones)
    assert all(fila["aplicada_en"] for fila in recomendaciones)

    proyecto = cliente.get(f"/proyectos/{proyecto_id}").json()
    assert proyecto["corrida_actual_id"] == inicio["corrida_id"]


def test_aplicar_no_cambia_el_intake(cliente_autenticado: TestClient) -> None:
    """Aplicar y volver a pedir el análisis no debe gastar otra corrida."""

    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    primera = _iniciar(cliente, proyecto_id)
    aplicar = cliente.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{primera['corrida_id']}/aplicar"
    )
    assert aplicar.status_code == 200, aplicar.text

    segunda = cliente.post(f"/proyectos/{proyecto_id}/agente")
    assert segunda.status_code == 200, segunda.text
    assert segunda.json()["corrida_id"] == primera["corrida_id"]
    assert segunda.json()["intake_hash"] == primera["intake_hash"]


def test_aplicar_dos_veces_responde_409(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    inicio = _iniciar(cliente, proyecto_id)
    ruta = f"/proyectos/{proyecto_id}/agente/corridas/{inicio['corrida_id']}/aplicar"

    assert cliente.post(ruta).status_code == 200
    segunda = cliente.post(ruta)
    assert segunda.status_code == 409, segunda.text


def test_aplicar_corrida_inexistente_404(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    respuesta = cliente.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{uuid.uuid4()}/aplicar"
    )
    assert respuesta.status_code == 404, respuesta.text


def test_recomendaciones_se_persisten_por_cultivo_y_advertencia(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    inicio = _iniciar(cliente, proyecto_id)
    detalle = _detalle(cliente, proyecto_id, inicio["corrida_id"])

    filas = (
        db_session.query(AgenteRecomendacion)
        .filter(AgenteRecomendacion.corrida_id == uuid.UUID(inicio["corrida_id"]))
        .all()
    )
    tipos = [fila.tipo for fila in filas]
    assert tipos.count("cultivo") == len(detalle["salida"]["cultivos"])
    assert tipos.count("sistema_riego") == 1
    assert tipos.count("advertencia") == len(detalle["salida"]["advertencias"])


# --------------------------------------------------------------------------- #
# S4 — correcciones determinísticas del backend
# --------------------------------------------------------------------------- #


def _propuesta_cruda() -> PropuestaAgente:
    return PropuestaAgente(
        cultivos=[
            CultivoRecomendado(
                cultivo_codigo="papa",
                nombre="Papa inventada",
                color="#000000",
                area_m2=500.0,
                demanda_l_m2_dia=9.0,
                ciclo_dias=None,
                siembra_sugerida=date(2026, 5, 1),
                cosecha_sugerida=date(2026, 4, 1),
                justificacion="  ",
                fuente_ids=[7, 9],
            ),
            CultivoRecomendado(
                cultivo_codigo="quinoa",
                nombre="Quinoa",
                area_m2=50.0,
                demanda_l_m2_dia=1.0,
                justificacion="Fuera de catálogo.",
            ),
        ],
        sistema=SistemaRecomendado(
            tipo="aspersión",
            emisor=EmisorRecomendado(tipo="gotero", caudal_lh=5, separacion_m=1.9),
            separacion_laterales_m=7.5,
            bomba_hp=7,
            num_sectores=6,
        ),
    )


def test_corregir_la_propuesta_del_modelo() -> None:
    corregida = corregir(
        _propuesta_cruda(),
        catalogo={
            codigo: {
                "codigo": codigo,
                "nombre": datos["nombre"],
                "color": datos["color"],
                "demanda_agua_l_m2_dia": datos["demanda"],
                "ciclo_dias": datos["ciclo"],
            }
            for codigo, datos in CATALOGO.items()
        },
        area_m2=AREA_TERRENO,
        total_fuentes=2,
    )

    codigos = {alerta.codigo for alerta in corregida.advertencias}
    assert {
        "CULTIVO_FUERA_DE_CATALOGO",
        "AREA_AJUSTADA",
        "DEMANDA_AJUSTADA",
        "FECHAS_AJUSTADAS",
        "RIEGO_AJUSTADO",
    } <= codigos

    assert [cultivo.cultivo_codigo for cultivo in corregida.cultivos] == ["papa"]
    papa = corregida.cultivos[0]
    assert papa.nombre == "Papa"
    assert papa.color == "#8D6E63"
    assert papa.area_m2 <= AREA_TERRENO
    assert papa.demanda_l_m2_dia == 2.0
    assert papa.ciclo_dias == 120
    assert papa.siembra_sugerida == date(2026, 5, 1)
    assert papa.cosecha_sugerida > papa.siembra_sugerida
    # Los índices inventados por el modelo se reemplazan por las fuentes que
    # realmente se recuperaron en la corrida (1-based).
    assert papa.fuente_ids == [1, 2]
    assert papa.justificacion

    sistema = corregida.sistema
    assert sistema.tipo == "goteo"
    assert sistema.emisor.caudal_lh == 4.0
    assert sistema.emisor.separacion_m == 1.0
    assert sistema.separacion_laterales_m == 7.5
    assert sistema.bomba_hp == 2.0
    assert sistema.num_sectores == 6


def test_corregir_sin_cultivos_de_catalogo_falla() -> None:
    propuesta = _propuesta_cruda()
    propuesta.cultivos = [
        cultivo for cultivo in propuesta.cultivos if cultivo.cultivo_codigo == "quinoa"
    ]
    with pytest.raises(PropuestaInvalida):
        corregir(
            propuesta,
            catalogo={"papa": {"nombre": "Papa", "color": "#8D6E63", "demanda_agua_l_m2_dia": 2.0}},
            area_m2=AREA_TERRENO,
            total_fuentes=0,
        )


def test_repartir_porcentajes_no_excede_el_cien() -> None:
    areas = [33.33, 33.33, 33.34]
    porcentajes = repartir_porcentajes(areas, 100.0)
    assert sum(porcentajes) <= 100.0
    assert all(round(valor, 2) == valor for valor in porcentajes)

    tercios = repartir_porcentajes([100.0, 100.0, 100.0], 300.0)
    assert sum(tercios) <= 100.0

    parcial = repartir_porcentajes([50.0, 25.0], 200.0)
    assert sum(parcial) == pytest.approx(37.5, abs=0.01)


def test_entrada_huella_es_del_intake_no_de_la_salida() -> None:
    entrada = EntradaAgente(
        proyecto_id=uuid.uuid4(),
        productos=[ProductoDeseado(nombre="Papa", prioridad=1, area_deseada_m2=100)],
        area_m2=AREA_TERRENO,
        suelo_codigo="franco",
        fuente_agua="pozo",
        caudal_efectivo_m3h=3.0,
        caudal_origen="asumido",
        zona="Cuyo",
        pendiente_pct=2,
    )
    otra = entrada.model_copy(update={"area_m2": 300})

    assert entrada.huella() == entrada.huella()
    assert entrada.huella() != otra.huella()


def test_el_body_lleva_las_restricciones_del_paso_3(
    cliente_autenticado: TestClient,
) -> None:
    """S5: las restricciones del paso 3 llegan a la entrada congelada de la corrida."""
    proyecto_id = _proyecto_con_cultivos(cliente_autenticado)

    respuesta = cliente_autenticado.post(
        f"/proyectos/{proyecto_id}/agente",
        json={
            "restricciones": {
                "energia": "solar",
                "tanque_l": 5000,
                "presupuesto_bs": 1500,
            }
        },
    )
    assert respuesta.status_code == 202, respuesta.text

    detalle = _detalle(
        cliente_autenticado, proyecto_id, respuesta.json()["corrida_id"]
    )
    assert detalle["entrada"]["restricciones"] == {
        "energia": "solar",
        "tanque_l": 5000,
        "presupuesto_bs": 1500,
    }


def test_si_el_motor_no_genera_la_red_la_corrida_no_queda_aplicada(
    cliente_autenticado: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S8: sin red no hay informe, pero el usuario tiene que poder reintentar."""
    from app.services import riego as riego_service

    def fallar(_db, _proyecto):
        raise riego_service.RiegoServiceError(
            422, "El terreno no tiene área suficiente para repartir"
        )

    monkeypatch.setattr(riego_service, "generar", fallar)
    proyecto_id = _proyecto_con_cultivos(cliente_autenticado)
    corrida = _iniciar(cliente_autenticado, proyecto_id)

    aplicar = cliente_autenticado.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida['corrida_id']}/aplicar"
    )

    assert aplicar.status_code == 409, aplicar.text
    assert "no pudo generar la red de riego" in aplicar.text
    # No quedó en el callejón sin salida: el reintento no responde "ya está aplicada".
    reintento = cliente_autenticado.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida['corrida_id']}/aplicar"
    )
    assert "ya está aplicada" not in reintento.text
