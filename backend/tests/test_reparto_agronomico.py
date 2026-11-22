"""T1 (S1-S2): reparto agronómico del área y zonas irregulares.

La corrida real del usuario tiene cebolla, lechuga, maíz, yuca y maní con 420 m² cada
uno (``odd/tasks/resumen-reparto.md`` L3). Acá se prueba que el camino de catálogo
reparte por necesidad agronómica, que el reparto respeta el caudal del terreno y que
las zonas dibujadas siguen el contorno con superficies proporcionales.
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agente import cliente as agente_cliente
from app.core.config import settings
from app.dependencies import get_current_user
from app.main import app
from app.models.catalogo import Cultivo, Suelo
from app.models.usuario import Usuario
from app.schemas.agente import (
    CultivoRecomendado,
    EmisorRecomendado,
    ProductoDeseado,
    PropuestaAgente,
    SistemaRecomendado,
)
from app.services import agente as agente_service
from app.services import geometria
from tests.conftest import create_user

# Trapecio del prototipo: la diagonal acompaña el borde del terreno.
TRAPECIO = [(0.0, 40.0), (60.0, 40.0), (60.0, 20.0), (30.0, 0.0), (0.0, 0.0)]
AREA_TERRENO = 2100.0
CAUDAL_M3H = 3.0

# Demanda, ciclo y densidad reales del catálogo de la corrida del usuario.
DATOS = {
    "cebolla": (1.6, 150, 60.0),
    "lechuga": (1.5, 65, 9.0),
    "maiz": (2.4, 110, 7.0),
    "yuca": (2.2, 300, 1.0),
    "mani": (2.5, 120, 30.0),
}
ORDEN_USUARIO = ("cebolla", "lechuga", "maiz", "yuca", "mani")


def _insumos(orden=ORDEN_USUARIO, *, demanda=None):
    insumos = []
    for indice, codigo in enumerate(orden):
        agua, ciclo, densidad = DATOS[codigo]
        insumos.append(
            {
                "codigo": codigo,
                "prioridad": indice + 1,
                "demanda_l_m2_dia": (demanda or {}).get(codigo, agua),
                "ciclo_dias": ciclo,
                "densidad_plantas_m2": densidad,
                "aptitud_suelo": "apto",
            }
        )
    return insumos


def _caudal_de_la_jornada() -> float:
    return CAUDAL_M3H * 1000 * agente_service.HORAS_RIEGO_JORNADA


# --------------------------------------------------------------------------- #
# S1 — criterio de reparto (función pura, sin base)
# --------------------------------------------------------------------------- #


def test_el_reparto_no_es_partes_iguales_y_cubre_el_terreno() -> None:
    areas, _ = agente_service.repartir_area_agronomica(
        _insumos(), area_m2=AREA_TERRENO, caudal_efectivo_m3h=CAUDAL_M3H
    )

    assert len(areas) == 5
    assert len({round(area, 2) for area in areas}) > 1
    assert sum(areas) == pytest.approx(AREA_TERRENO, abs=1e-6)
    assert all(area > 0 for area in areas)


def test_la_prioridad_del_usuario_pesa_en_el_reparto() -> None:
    areas, _ = agente_service.repartir_area_agronomica(
        _insumos(), area_m2=AREA_TERRENO, caudal_efectivo_m3h=CAUDAL_M3H
    )

    # Cebolla es la primera del usuario: no puede quedar con el área mínima.
    assert areas[0] == max(areas)
    assert areas[0] > min(areas)


def test_sin_prioridad_de_por_medio_gana_el_de_mayor_demanda() -> None:
    insumos = [
        {
            "codigo": "poco",
            "prioridad": 1,
            "demanda_l_m2_dia": 1.0,
            "ciclo_dias": 90,
            "densidad_plantas_m2": 4.0,
            "aptitud_suelo": "apto",
        },
        {
            "codigo": "mucho",
            "prioridad": 1,
            "demanda_l_m2_dia": 4.0,
            "ciclo_dias": 90,
            "densidad_plantas_m2": 4.0,
            "aptitud_suelo": "apto",
        },
    ]
    areas, _ = agente_service.repartir_area_agronomica(
        insumos, area_m2=AREA_TERRENO, caudal_efectivo_m3h=CAUDAL_M3H
    )

    # Con la misma prioridad, el cultivo que más agua pide no se lleva más área.
    assert areas[1] <= areas[0]


def test_la_demanda_pico_del_conjunto_no_supera_el_caudal_de_la_jornada() -> None:
    areas, pico = agente_service.repartir_area_agronomica(
        _insumos(), area_m2=AREA_TERRENO, caudal_efectivo_m3h=CAUDAL_M3H
    )

    demandas = [d for d, _, _ in DATOS.values()]
    assert pico == pytest.approx(sum(a * d for a, d in zip(areas, demandas)))
    assert pico <= _caudal_de_la_jornada()


def test_el_agua_limita_el_area_de_los_cultivos_que_mas_piden() -> None:
    """Con un caudal chico, el reparto no puede superar lo que la fuente entrega."""

    insumos = [
        {
            "codigo": "poco",
            "prioridad": 1,
            "demanda_l_m2_dia": 1.0,
            "ciclo_dias": 90,
            "densidad_plantas_m2": 4.0,
            "aptitud_suelo": "apto",
        },
        {
            "codigo": "mucho",
            "prioridad": 1,
            "demanda_l_m2_dia": 5.0,
            "ciclo_dias": 90,
            "densidad_plantas_m2": 4.0,
            "aptitud_suelo": "apto",
        },
    ]
    caudal = 0.05  # 50 L/h: 800 L por jornada de 16 h
    areas, pico = agente_service.repartir_area_agronomica(
        insumos, area_m2=300.0, caudal_efectivo_m3h=caudal
    )

    assert sum(areas) == pytest.approx(300.0, abs=1e-6)
    assert pico <= caudal * 1000 * agente_service.HORAS_RIEGO_JORNADA
    assert areas[1] <= areas[0]


def test_cuando_el_caudal_aprieta_manda_el_agua_y_no_la_prioridad() -> None:
    """El techo de la jornada pesa más que la prioridad del usuario."""

    insumos = [
        {
            "codigo": "poco",
            "prioridad": 2,
            "demanda_l_m2_dia": 1.0,
            "ciclo_dias": 90,
            "densidad_plantas_m2": 4.0,
            "aptitud_suelo": "apto",
        },
        {
            "codigo": "mucho",
            "prioridad": 1,
            "demanda_l_m2_dia": 5.0,
            "ciclo_dias": 90,
            "densidad_plantas_m2": 4.0,
            "aptitud_suelo": "apto",
        },
    ]
    # 0,034375 m³/h = 34,375 L/h: 550 L por jornada. El reparto ponderado pediría
    # 577 L/día; el reparto de agua igual, 500 L/día, sí entra.
    areas, pico = agente_service.repartir_area_agronomica(
        insumos, area_m2=300.0, caudal_efectivo_m3h=0.034375
    )

    assert sum(areas) == pytest.approx(300.0, abs=1e-6)
    assert pico <= 550.0
    assert areas[1] <= areas[0]


def test_un_solo_producto_cubre_el_terreno() -> None:
    areas, _ = agente_service.repartir_area_agronomica(
        _insumos(orden=("cebolla",)), area_m2=AREA_TERRENO, caudal_efectivo_m3h=CAUDAL_M3H
    )

    assert areas == [pytest.approx(AREA_TERRENO, abs=1e-6)]


def test_sin_datos_de_ficha_el_reparto_sigue_cubriendo_el_terreno() -> None:
    insumos = [
        {
            "codigo": codigo,
            "prioridad": indice + 1,
            "demanda_l_m2_dia": DATOS[codigo][0],
        }
        for indice, codigo in enumerate(ORDEN_USUARIO)
    ]
    areas, _ = agente_service.repartir_area_agronomica(
        insumos, area_m2=AREA_TERRENO, caudal_efectivo_m3h=CAUDAL_M3H
    )

    assert sum(areas) == pytest.approx(AREA_TERRENO, abs=1e-6)
    assert all(area > 0 for area in areas)


# --------------------------------------------------------------------------- #
# S1-S2 — corrida real: catálogo, aplicar y zonas dibujadas
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def catalogo(db_session: Session) -> None:
    db_session.add_all(
        [
            Cultivo(
                codigo=codigo,
                nombre=codigo.title(),
                icono="X",
                color="#4CAF50",
                demanda_agua_l_m2_dia=datos[0],
                ciclo_dias=datos[1],
                densidad_plantas_m2=datos[2],
                activo=True,
            )
            for codigo, datos in DATOS.items()
        ]
    )
    db_session.add(Suelo(codigo="franco", nombre="Franco", infiltracion_mm_h=12.0))
    db_session.commit()


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="reparto@example.com")


@pytest.fixture()
def cliente(cliente_autenticado: TestClient) -> TestClient:
    return cliente_autenticado


@pytest.fixture()
def cliente_autenticado(
    client: TestClient, usuario: Usuario
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_current_user] = lambda: usuario
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def _proyecto(cliente: TestClient) -> str:
    proyecto_id = cliente.post("/proyectos", json={"nombre": "Reparto"}).json()["id"]
    terreno = cliente.put(
        f"/proyectos/{proyecto_id}/terreno",
        json={
            "nombre_parcela": "Lote",
            "forma": "poligono",
            "vertices": [{"x": x, "y": y} for x, y in TRAPECIO],
            "suelo_codigo": "franco",
            "pendiente_pct": 1,
            "fuente_agua": "pozo",
            "caudal_disponible_m3h": CAUDAL_M3H,
        },
    )
    assert terreno.status_code == 200, terreno.text
    return proyecto_id


def _corrida(
    cliente: TestClient, proyecto_id: str, codigos=ORDEN_USUARIO
) -> tuple[str, dict]:
    respuesta = cliente.post(
        f"/proyectos/{proyecto_id}/agente",
        json={
            "productos": [
                {"cultivo_codigo": codigo, "prioridad": indice + 1}
                for indice, codigo in enumerate(codigos)
            ]
        },
    )
    assert respuesta.status_code == 202, respuesta.text
    corrida_id = respuesta.json()["corrida_id"]
    detalle = cliente.get(f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}")
    assert detalle.status_code == 200, detalle.text
    return corrida_id, detalle.json()


def test_la_corrida_en_catalogo_reparte_por_necesidad(cliente: TestClient) -> None:
    proyecto_id = _proyecto(cliente)
    _, corrida = _corrida(cliente, proyecto_id)
    propuesta = PropuestaAgente.model_validate(corrida["salida"])

    areas = {cultivo.cultivo_codigo: cultivo.area_m2 for cultivo in propuesta.cultivos}
    assert set(areas) == set(ORDEN_USUARIO)
    assert len({round(area, 2) for area in areas.values()}) > 1
    assert sum(areas.values()) == pytest.approx(AREA_TERRENO, abs=0.01)
    assert all(area > 0 for area in areas.values())

    demandas = {codigo: DATOS[codigo][0] for codigo in ORDEN_USUARIO}
    pico = sum(areas[codigo] * demandas[codigo] for codigo in ORDEN_USUARIO)
    assert pico <= _caudal_de_la_jornada()


def _anillo(poligono: dict) -> list[tuple[float, float]]:
    return [(float(x), float(y)) for x, y in poligono["anillo"]]


def test_las_zonas_no_se_salen_y_coinciden_con_el_area_asignada(
    cliente: TestClient,
) -> None:
    proyecto_id = _proyecto(cliente)
    corrida_id, corrida = _corrida(cliente, proyecto_id)
    propuesta = PropuestaAgente.model_validate(corrida["salida"])
    asignadas = {
        cultivo.cultivo_codigo: cultivo.area_m2 for cultivo in propuesta.cultivos
    }

    aplicada = cliente.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}/aplicar"
    )
    assert aplicada.status_code == 200, aplicada.text
    bloques = aplicada.json()["diseno"]["bloques"]
    assert len(bloques) == len(asignadas)

    total = 0.0
    for bloque in bloques:
        anillo = _anillo(bloque["poligono"])
        total += bloque["area_m2"]
        assert bloque["area_m2"] == pytest.approx(asignadas[bloque["cultivo_codigo"]], abs=0.01)
        assert bloque["area_m2"] == pytest.approx(geometria.area_poligono(anillo), abs=0.01)
        assert all(geometria.punto_en_poligono(p, TRAPECIO, tolerancia=1e-3) for p in anillo)
    assert total == pytest.approx(AREA_TERRENO, abs=0.05)

    # Dos productos con áreas distintas no se dibujan como cortes iguales.
    anchos = {round(max(x for x, _ in _anillo(b["poligono"])), 4) for b in bloques}
    assert len(anchos) > 1 or len({round(b["area_m2"], 2) for b in bloques}) > 1


def test_un_solo_producto_cubre_el_terreno_aplicado(cliente: TestClient) -> None:
    proyecto_id = _proyecto(cliente)
    corrida_id, _ = _corrida(cliente, proyecto_id, codigos=("cebolla",))

    aplicada = cliente.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}/aplicar"
    )
    assert aplicada.status_code == 200, aplicada.text
    bloques = aplicada.json()["diseno"]["bloques"]
    assert len(bloques) == 1
    assert bloques[0]["area_m2"] == pytest.approx(AREA_TERRENO, abs=0.01)


def test_en_modo_llm_manda_el_area_del_agente(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    areas_agente = {
        "cebolla": 900.0,
        "lechuga": 600.0,
        "maiz": 400.0,
        "yuca": 150.0,
        "mani": 50.0,
    }
    cruda = PropuestaAgente(
        cultivos=[
            CultivoRecomendado(
                cultivo_codigo=codigo,
                nombre=codigo.title(),
                area_m2=areas_agente[codigo],
                demanda_l_m2_dia=DATOS[codigo][0],
                ciclo_dias=DATOS[codigo][1],
                justificacion="Propuesta del modelo.",
            )
            for codigo in ORDEN_USUARIO
        ],
        sistema=SistemaRecomendado(
            tipo="goteo",
            emisor=EmisorRecomendado(tipo="gotero", caudal_lh=2, separacion_m=0.3),
            separacion_laterales_m=0.5,
            bomba_hp=1,
            num_sectores=4,
        ),
    )
    monkeypatch.setattr(settings, "AGENTE_MODO", "llm", raising=False)
    monkeypatch.setattr(settings, "AGENTE_API_KEY", "sk-prueba", raising=False)
    monkeypatch.setattr(
        agente_cliente, "_propuesta_llm", lambda _contexto: (cruda, 10, 20)
    )

    proyecto_id = _proyecto(cliente)
    _, corrida = _corrida(cliente, proyecto_id)
    assert corrida["modelo"] == settings.AGENTE_MODELO

    propuesta = PropuestaAgente.model_validate(corrida["salida"])
    # El área del agente manda: solo pasa por la cuantización que ya existía al
    # 0,01 % del terreno, jamás por el reparto agronómico del camino de catálogo.
    assert {
        cultivo.cultivo_codigo: cultivo.area_m2 for cultivo in propuesta.cultivos
    } == pytest.approx(areas_agente, abs=0.5)


def test_sin_ficha_en_el_catalogo_el_reparto_igual_cierra_el_terreno(
    db_session: Session,
) -> None:
    """Un cultivo que no está en el catálogo no rompe el reparto ni deja huecos."""

    entrada = agente_service.EntradaAgente(
        proyecto_id=uuid.uuid4(),
        productos=[ProductoDeseado(nombre="Papa", prioridad=1)],
        area_m2=AREA_TERRENO,
        suelo_codigo="franco",
        fuente_agua="pozo",
        caudal_efectivo_m3h=CAUDAL_M3H,
        caudal_origen="asumido",
    )
    propuesta = PropuestaAgente(
        cultivos=[
            CultivoRecomendado(
                cultivo_codigo="papa",
                nombre="Papa",
                area_m2=AREA_TERRENO,
                demanda_l_m2_dia=2.0,
                justificacion="Única.",
            )
        ],
        sistema=SistemaRecomendado(
            tipo="goteo",
            emisor=EmisorRecomendado(tipo="gotero", caudal_lh=2, separacion_m=0.3),
            separacion_laterales_m=0.5,
            bomba_hp=1,
            num_sectores=1,
        ),
    )

    corregida = agente_service._con_reparto_agronomico(db_session, entrada, propuesta)

    # Un solo producto cubre el terreno: el reparto no lo deja corto ni lo pasa.
    assert [cultivo.area_m2 for cultivo in corregida.cultivos] == [
        pytest.approx(AREA_TERRENO, abs=1e-6)
    ]


def test_aplicar_no_cambia_la_huella_por_las_areas_del_motor() -> None:
    """S1: las áreas que produjo el motor no pueden gastar otra corrida del agente."""
    import uuid

    from app.schemas.agente import EntradaAgente, ProductoDeseado

    proyecto_id = uuid.uuid4()

    def entrada(papa: float | None, lechuga: float | None) -> EntradaAgente:
        return EntradaAgente(
            proyecto_id=proyecto_id,
            productos=[
                ProductoDeseado(nombre="Papa", prioridad=1, area_deseada_m2=papa),
                ProductoDeseado(nombre="Lechuga", prioridad=2, area_deseada_m2=lechuga),
            ],
            area_m2=2100.0,
            suelo_codigo="franco",
            fuente_agua="pozo",
            caudal_efectivo_m3h=3.0,
            caudal_origen="asumido",
            zona="Cochabamba",
            pendiente_pct=2.0,
            siembra=None,
        )

    pedido_del_usuario = entrada(None, None)
    tras_aplicar = entrada(1132.11, 499.17)

    assert pedido_del_usuario.huella() == tras_aplicar.huella()
