"""Alta de productos que no estaban en el catálogo.

S5-S7: el usuario escribe un producto libre, el backend lo resuelve con la ficha
curada primero y con búsqueda web como respaldo, da de alta la ficha con sus fuentes
y avisa. S8: lo investigado sólo aporta datos agronómicos; el resto sigue siendo del
motor determinístico.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agente.cliente import FuenteRecuperada
from app.agente.investigacion import Investigacion
from app.dependencies import get_current_user
from app.main import app
from app.models.catalogo import Cultivo, Suelo
from app.models.usuario import Usuario
from tests.conftest import create_user


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="productos@example.com")


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
            Suelo(codigo="franco", nombre="Franco", infiltracion_mm_h=12.0),
        ]
    )
    db_session.commit()


def _proyecto(cliente: TestClient) -> str:
    proyecto = cliente.post("/proyectos", json={"nombre": "Finca Productos"})
    assert proyecto.status_code == 201, proyecto.text
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
        },
    )
    assert terreno.status_code == 200, terreno.text
    return proyecto_id


def _alta(cliente: TestClient, proyecto_id: str, **cuerpo) -> dict:
    respuesta = cliente.post(f"/proyectos/{proyecto_id}/cultivos", json=cuerpo)
    return {"status": respuesta.status_code, "cuerpo": respuesta.json()}


# --------------------------------------------------------------------------- #
# Ficha curada: camino feliz sin red
# --------------------------------------------------------------------------- #


def test_producto_con_ficha_curada_se_da_de_alta(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)

    alta = _alta(
        cliente,
        proyecto_id,
        producto_texto="quinoa",
        modo="porcentaje",
        porcentaje=40,
    )
    assert alta["status"] == 201, alta
    bloque = alta["cuerpo"]["bloque"]
    assert bloque["cultivo_codigo"] == "quinoa"
    assert bloque["area_m2"] == 80

    codigos = [alerta["codigo"] for alerta in alta["cuerpo"]["advertencias"]]
    assert codigos == ["CULTIVO_DESDE_FICHA"]
    assert alta["cuerpo"]["advertencias"][0]["bloqueante"] is False

    quinoa = db_session.query(Cultivo).filter_by(codigo="quinoa").one()
    assert quinoa.origen == "humano"  # ficha curada en el repo: ya está revisada
    assert quinoa.revisado_en is not None
    assert quinoa.fuentes
    assert quinoa.demanda_agua_l_m2_dia > 0
    assert quinoa.ciclo_dias > 0


def test_el_agente_disenia_con_un_producto_de_ficha_curada(
    cliente_autenticado: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El caso que rompía la demo: un producto fuera del catálogo con ficha curada.

    El paso 4 resuelve el producto antes de correr: sin ficha y sin web la corrida
    moría con 422. Con la ficha de chía la corrida termina y recomienda el cultivo.
    """

    from app.core.config import settings

    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)
    # Sin clave el agente corre en modo catálogo: determinístico y sin gastar tokens.
    monkeypatch.setattr(settings, "AGENTE_API_KEY", "", raising=False)

    disparo = cliente.post(
        f"/proyectos/{proyecto_id}/agente",
        json={"productos": [{"producto_texto": "Chía"}]},
    )
    assert disparo.status_code == 202, disparo.text

    corrida = cliente.get(f"/agente/corridas/{disparo.json()['corrida_id']}").json()
    assert (corrida["estado"], corrida["fase"]) == ("ok", "listo")

    codigos = [aviso["codigo"] for aviso in corrida["salida"]["advertencias"]]
    assert "PRODUCTO_NO_RECONOCIDO" not in codigos
    assert any(
        (cultivo["cultivo_codigo"] or "").startswith("chia")
        for cultivo in corrida["salida"]["cultivos"]
    )


def test_producto_con_ficha_curada_no_duplica_el_cultivo(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)

    assert _alta(
        cliente, proyecto_id, producto_texto="Quínoa", modo="porcentaje", porcentaje=30
    )["status"] == 201
    assert _alta(
        cliente, proyecto_id, producto_texto="quinoa", modo="porcentaje", porcentaje=30
    )["status"] == 201

    assert db_session.query(Cultivo).filter_by(codigo="quinoa").count() == 1


def test_producto_con_ficha_entra_al_flujo_del_agente(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)

    _alta(cliente, proyecto_id, producto_texto="quinoa", modo="porcentaje", porcentaje=50)
    _alta(cliente, proyecto_id, cultivo_codigo="papa", modo="porcentaje", porcentaje=50)

    inicio = cliente.post(f"/proyectos/{proyecto_id}/agente")
    assert inicio.status_code == 202, inicio.text
    detalle = cliente.get(
        f"/proyectos/{proyecto_id}/agente/corridas/{inicio.json()['corrida_id']}"
    ).json()

    assert detalle["estado"] == "ok", detalle["error_detalle"]
    codigos = {cultivo["cultivo_codigo"] for cultivo in detalle["salida"]["cultivos"]}
    assert codigos == {"papa", "quinoa"}


# --------------------------------------------------------------------------- #
# Alta automática desde web: aviso bloqueante y trazabilidad
# --------------------------------------------------------------------------- #


def test_ficha_investigada_en_web_queda_marcada_y_avisada(
    cliente_autenticado: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)

    def investigacion_falsa(nombre, *, catalogo, busqueda_web=None, max_busquedas=None):
        return Investigacion(
            codigo="moringa",
            nombre="Moringa",
            icono="M",
            color="#2E7D32",
            demanda_agua_l_m2_dia=1.8,
            ciclo_dias=180,
            meses_siembra=[9, 10],
            notas="Investigada en web para la prueba.",
            fuentes=[
                FuenteRecuperada(
                    tipo="web",
                    titulo="Ficha de moringa",
                    url="https://example.org/moringa",
                    fragmento="Demanda aproximada de 1,8 L/m2/dia.",
                )
            ],
            origen="web",
            busquedas=1,
        )

    monkeypatch.setattr("app.agente.investigacion.investigar", investigacion_falsa)

    alta = _alta(
        cliente, proyecto_id, producto_texto="moringa", modo="porcentaje", porcentaje=25
    )
    assert alta["status"] == 201, alta
    assert alta["cuerpo"]["bloque"]["cultivo_codigo"] == "moringa"

    aviso = alta["cuerpo"]["advertencias"][0]
    assert aviso["codigo"] == "CULTIVO_INVESTIGADO"
    assert aviso["bloqueante"] is True

    moringa = db_session.query(Cultivo).filter_by(codigo="moringa").one()
    assert moringa.origen == "agente"
    assert moringa.revisado_en is None
    assert moringa.fuentes[0]["url"] == "https://example.org/moringa"
    assert moringa.fuentes[0]["tipo"] == "web"

    # La ficha queda visible en el catálogo con su procedencia.
    listado = cliente.get("/catalogos/cultivos").json()
    ficha = next(fila for fila in listado if fila["codigo"] == "moringa")
    assert ficha["origen"] == "agente"
    assert ficha["revisado_en"] is None
    assert ficha["fuentes"]


def test_lo_investigado_no_toca_los_parametros_del_motor(
    cliente_autenticado: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S8: la web sólo aporta la ficha agronómica, nunca el diseño hidráulico."""

    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)

    def investigacion_falsa(nombre, *, catalogo, busqueda_web=None, max_busquedas=None):
        assert busqueda_web is None or callable(busqueda_web)
        return Investigacion(
            codigo="moringa",
            nombre="Moringa",
            icono="M",
            color="#2E7D32",
            demanda_agua_l_m2_dia=1.8,
            ciclo_dias=180,
            meses_siembra=None,
            notas="sin diseño hidráulico",
            fuentes=[
                FuenteRecuperada(tipo="web", titulo="t", url="https://e.org/m", fragmento="f")
            ],
            origen="web",
            busquedas=1,
        )

    monkeypatch.setattr("app.agente.investigacion.investigar", investigacion_falsa)
    assert _alta(
        cliente, proyecto_id, producto_texto="moringa", modo="porcentaje", porcentaje=50
    )["status"] == 201
    assert _alta(
        cliente, proyecto_id, cultivo_codigo="papa", modo="porcentaje", porcentaje=50
    )["status"] == 201

    corrida_id = cliente.post(f"/proyectos/{proyecto_id}/agente").json()["corrida_id"]
    aplicar = cliente.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}/aplicar"
    )
    assert aplicar.status_code == 200, aplicar.text

    sistema = aplicar.json()["diseno"]["sistema"]
    # El riego sale del motor y del terreno, no de la ficha investigada.
    assert sistema["fuente_agua"] == "pozo"
    assert sistema["emisor"]["caudal_lh"] in (2, 4, 8)
    assert sistema["bomba_hp"] in (0.5, 1, 1.5, 2)


def test_lo_investigado_respeta_los_anchos_de_la_tabla(
    cliente_autenticado: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un nombre de 200 caracteres no puede romper en PostgreSQL ni entrar crudo."""

    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)
    nombre_largo = "Moringa peregrina variedad altísima de los Andes " * 4

    def investigacion_falsa(nombre, *, catalogo, busqueda_web=None, max_busquedas=None):
        return Investigacion(
            codigo="moringa",
            nombre=nombre_largo,
            icono="M",
            color="#2E7D32",
            demanda_agua_l_m2_dia=1.8,
            ciclo_dias=180,
            meses_siembra=None,
            notas="x" * 900,
            fuentes=[
                FuenteRecuperada(tipo="web", titulo="t", url="https://e.org/m", fragmento="f")
            ],
            origen="web",
            busquedas=1,
        )

    monkeypatch.setattr("app.agente.investigacion.investigar", investigacion_falsa)

    # El sanear de la investigación no participa acá (el fake la saltea), así que el
    # límite tiene que caer en la escritura: es lo que se verifica.
    alta = _alta(
        cliente, proyecto_id, producto_texto="moringa", modo="porcentaje", porcentaje=20
    )
    assert alta["status"] == 201, alta
    moringa = db_session.query(Cultivo).filter_by(codigo="moringa").one()
    assert len(moringa.nombre) <= 60


def test_lo_investigado_se_recorta_antes_de_salir_del_agente() -> None:
    """El saneo real de la investigación recorta el nombre al ancho de la tabla."""

    from app.agente.investigacion import investigar

    def busqueda_web(_consulta: str) -> list[dict]:
        return [
            {
                "titulo": "Ficha",
                "url": "https://e.org/moringa",
                "demanda_agua_l_m2_dia": 1.8,
                "ciclo_dias": 180,
                "nombre": "Moringa " * 40,
            }
        ]

    investigacion = investigar(
        "moringa", catalogo=[], busqueda_web=busqueda_web, max_busquedas=1
    )
    assert investigacion.origen == "web"
    assert len(investigacion.nombre) <= 60


# --------------------------------------------------------------------------- #
# Sin verificación no hay cultivo
# --------------------------------------------------------------------------- #


def test_producto_sin_ficha_y_sin_web_no_se_inventa(
    cliente_autenticado: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import settings

    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)
    monkeypatch.setattr(settings, "AGENTE_API_KEY", "", raising=False)

    alta = _alta(
        cliente, proyecto_id, producto_texto="planta rara", modo="porcentaje", porcentaje=20
    )
    assert alta["status"] == 422, alta
    assert "No se pudo verificar" in alta["cuerpo"]["detail"]
    # El motivo real es lo único accionable: sustituirlo por un texto fijo deja al
    # usuario sin saber si le falta la clave, la ficha o la respuesta de la web.
    assert "AGENTE_API_KEY" in alta["cuerpo"]["detail"]
    # El mismo tope de 300 que usan las demás advertencias: el detalle viaja al usuario.
    assert len(alta["cuerpo"]["detail"]) <= 300

    bloques = cliente.get(f"/proyectos/{proyecto_id}/cultivos").json()
    assert bloques == []


# --------------------------------------------------------------------------- #
# Contrato del payload
# --------------------------------------------------------------------------- #


def test_no_se_pueden_mandar_codigo_y_producto(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)

    alta = _alta(
        cliente,
        proyecto_id,
        cultivo_codigo="papa",
        producto_texto="quinoa",
        modo="porcentaje",
        porcentaje=10,
    )
    assert alta["status"] == 422, alta


def test_hace_falta_codigo_o_producto(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)

    alta = _alta(cliente, proyecto_id, modo="porcentaje", porcentaje=10)
    assert alta["status"] == 422, alta


def test_el_codigo_del_catalogo_sigue_funcionando(cliente_autenticado: TestClient) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto(cliente)

    alta = _alta(cliente, proyecto_id, cultivo_codigo="papa", modo="porcentaje", porcentaje=50)
    assert alta["status"] == 201, alta
    assert alta["cuerpo"]["advertencias"] == []

    desconocido = _alta(
        cliente, proyecto_id, cultivo_codigo="noexistecultivo", modo="porcentaje", porcentaje=10
    )
    assert desconocido["status"] == 422
    assert desconocido["cuerpo"]["detail"] == (
        "El cultivo 'noexistecultivo' no existe o está inactivo"
    )
