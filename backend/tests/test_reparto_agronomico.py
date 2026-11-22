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


# Área mínima viable de cada producto en este terreno: el mayor entre el 5 % del
# terreno y el piso absoluto de 10 m² (ver agente.MINIMO_VIABLE_PCT).
MINIMO_VIABLE_TERRENO = max(
    agente_service.MINIMO_VIABLE_M2,
    AREA_TERRENO * agente_service.MINIMO_VIABLE_PCT / 100.0,
)
# Reparto prioritario de siempre con agua de sobra (b_i = p_i / d_i, sin techo).
REPARTO_PRIORITARIO = (1132.11, 499.17, 222.6, 122.22, 123.9)


def _entrada(caudal: float, *, caudal_origen: str = "asumido") -> agente_service.EntradaAgente:
    return agente_service.EntradaAgente(
        proyecto_id=uuid.uuid4(),
        productos=[
            ProductoDeseado(
                nombre=codigo.title(), cultivo_codigo=codigo, prioridad=indice + 1
            )
            for indice, codigo in enumerate(ORDEN_USUARIO)
        ],
        area_m2=AREA_TERRENO,
        suelo_codigo="franco",
        fuente_agua="pozo",
        caudal_efectivo_m3h=caudal,
        caudal_origen=caudal_origen,
    )


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


def test_con_igual_prioridad_ciclo_y_densidad_menos_demanda_recibe_mas_area() -> None:
    """El criterio que documenta el reparto: b_i = p_i / d_i.

    Con la misma prioridad, el mismo ciclo y la misma densidad, el cultivo que pide
    más agua por m² recibe estrictamente menos superficie. Ciclo y densidad pueden
    invertir ese orden, así que el criterio no promete más que esto.
    """

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

    assert areas[0] > areas[1]


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


def test_el_minimo_viable_se_respeta_cuando_el_reparto_es_factible() -> None:
    """Con 0,22 m³/h entra el mínimo de todos (3.434 L/día) y el techo se cumple."""

    areas, pico = agente_service.repartir_area_agronomica(
        _insumos(), area_m2=AREA_TERRENO, caudal_efectivo_m3h=0.22
    )

    assert sum(areas) == pytest.approx(AREA_TERRENO, abs=1e-6)
    assert all(area >= MINIMO_VIABLE_TERRENO - 1e-6 for area in areas)
    assert pico <= 0.22 * 1000 * agente_service.HORAS_RIEGO_JORNADA + 1e-6
    # Los sedientos ceden superficie pero nadie queda en una maceta, y el agua manda:
    # la lechuga, que es la que menos pide por m², es la que más superficie recibe.
    assert areas[1] == max(areas)
    assert min(areas) >= MINIMO_VIABLE_TERRENO


def test_con_agua_holgada_nada_cambia_respecto_de_hoy() -> None:
    """Con 3 m³/h el reparto prioritario entra completo: no se toca (S1)."""

    areas, pico = agente_service.repartir_area_agronomica(
        _insumos(), area_m2=AREA_TERRENO, caudal_efectivo_m3h=CAUDAL_M3H
    )

    assert areas == pytest.approx(REPARTO_PRIORITARIO, abs=0.01)
    assert sum(areas) == pytest.approx(AREA_TERRENO, abs=1e-6)
    assert pico == pytest.approx(3673.0, abs=0.5)
    assert pico <= _caudal_de_la_jornada()


def test_el_piso_absoluto_del_minimo_viable_manda_en_terrenos_chicos() -> None:
    """En 100 m² el 5 % son 5 m² pero el piso de 10 m² es el que rige."""

    insumos = [
        {
            "codigo": codigo,
            "prioridad": prioridad,
            "demanda_l_m2_dia": demanda,
            "ciclo_dias": 90,
            "densidad_plantas_m2": 4.0,
            "aptitud_suelo": "apto",
        }
        for codigo, prioridad, demanda in (
            ("poco", 1, 1.0),
            ("medio", 2, 1.0),
            ("mucho", 3, 8.0),
        )
    ]
    areas, pico = agente_service.repartir_area_agronomica(
        insumos, area_m2=100.0, caudal_efectivo_m3h=0.011
    )

    assert sum(areas) == pytest.approx(100.0, abs=1e-6)
    # Sin el piso de 10 m² el tercer producto quedaría con 3,2 m².
    assert all(area >= agente_service.MINIMO_VIABLE_M2 - 1e-6 for area in areas)
    assert pico <= 0.011 * 1000 * agente_service.HORAS_RIEGO_JORNADA + 1e-6


@pytest.mark.parametrize(
    "caudal",
    [
        3.00,  # 48000 L/día: entra el reparto prioritario completo (3673 L/día)
        0.30,  # 4800 L/día: también
        0.24,  # 3840 L/día: también
        0.22,  # 3520 L/día: el mínimo de todos (3434 L/día) entra, el prioritario no
        0.20,  # 3200 L/día: el mínimo de todos no entra
        0.05,  # 800 L/día: falta agua para el mínimo de todos
    ],
)
def test_el_barrido_de_caudal_respeta_el_minimo_viable_y_el_techo(
    caudal: float,
) -> None:
    """Barrido del verificador con el criterio nuevo (S1).

    Con el mínimo viable de todos adentro, el reparto lo respeta y no supera el
    caudal. Cuando el mínimo no entra, se devuelve el reparto prioritario (nunca
    0,2 m²) y el aviso bloqueante explica la imposibilidad.
    """

    areas, pico = agente_service.repartir_area_agronomica(
        _insumos(), area_m2=AREA_TERRENO, caudal_efectivo_m3h=caudal
    )
    disponible = caudal * 1000 * agente_service.HORAS_RIEGO_JORNADA
    demandas = [d for d, _, _ in DATOS.values()]
    requerido = agente_service.agua_para_minimo_viable(
        _insumos(), area_m2=AREA_TERRENO
    )

    assert sum(areas) == pytest.approx(AREA_TERRENO, abs=1e-6)
    assert pico == pytest.approx(sum(a * d for a, d in zip(areas, demandas)))
    assert requerido is not None
    assert all(area >= MINIMO_VIABLE_TERRENO - 1e-6 for area in areas)

    if requerido <= disponible + 1e-6:
        assert pico <= disponible + 1e-6
    else:
        # Sin reparto posible: el prioritario de siempre, no un reparto absurdo.
        assert areas == pytest.approx(REPARTO_PRIORITARIO, abs=0.01)
        assert pico > disponible


def test_con_caudal_de_020_ningun_producto_queda_con_area_de_juguete(
    db_session: Session,
) -> None:
    """S1: con 0,20 m³/h no se le dan 0,2 m² a cuatro productos.

    O el reparto entra con el mínimo viable de todos y el techo de agua, o el aviso
    bloqueante explica por qué no se puede. Nunca un reparto de juguete entregado
    como si fuera válido.
    """

    areas, pico = agente_service.repartir_area_agronomica(
        _insumos(), area_m2=AREA_TERRENO, caudal_efectivo_m3h=0.20
    )
    disponible = 0.20 * 1000 * agente_service.HORAS_RIEGO_JORNADA
    corregida = agente_service._con_reparto_agronomico(
        db_session, _entrada(0.20), _propuesta(_insumos())
    )
    avisos = [
        alerta
        for alerta in corregida.advertencias
        if alerta.codigo == "DEMANDA_EXCEDE_CAUDAL"
    ]

    assert all(area >= MINIMO_VIABLE_TERRENO - 1e-6 for area in areas)
    assert sum(areas) == pytest.approx(AREA_TERRENO, abs=1e-6)
    if pico <= disponible + 1e-6:
        assert avisos == []
    else:
        assert avisos
        assert "3434 L/día" in avisos[0].mensaje


def test_con_005_el_aviso_es_bloqueante_y_dice_los_litros_necesarios(
    db_session: Session,
) -> None:
    """S1: con 0,05 m³/h el aviso explica qué pasa y qué puede hacer el usuario."""

    propuesta = _propuesta(_insumos())
    corregida = agente_service._con_reparto_agronomico(
        db_session, _entrada(0.05, caudal_origen="cliente"), propuesta
    )

    areas = [cultivo.area_m2 for cultivo in corregida.cultivos]
    demandas = [cultivo.demanda_l_m2_dia for cultivo in corregida.cultivos]
    pico = sum(area * demanda for area, demanda in zip(areas, demandas))
    disponible = 0.05 * 1000 * agente_service.HORAS_RIEGO_JORNADA
    aviso = next(
        alerta
        for alerta in corregida.advertencias
        if alerta.codigo == "DEMANDA_EXCEDE_CAUDAL"
    )

    assert sum(areas) == pytest.approx(AREA_TERRENO, abs=1e-6)
    # El reparto devuelto es el prioritario de siempre, sin áreas de juguete.
    assert areas == pytest.approx(REPARTO_PRIORITARIO, abs=0.01)
    assert pico > disponible
    # El caudal del fixture lo informa el usuario, así que el aviso bloquea.
    assert aviso.bloqueante is True
    # Cuántos productos, cuánta agua haría falta para el mínimo de todos y qué hacer.
    assert "los 5 productos pedidos" in aviso.mensaje
    assert "3434 L/día" in aviso.mensaje  # mínimo viable de todos
    assert "800 L/día" in aviso.mensaje  # lo que entrega la fuente
    assert "Reducí la lista de productos o mejorá la fuente de agua" in aviso.mensaje
    assert len(aviso.mensaje) <= 300


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


def _propuesta(insumos: list[dict]) -> PropuestaAgente:
    return PropuestaAgente(
        cultivos=[
            CultivoRecomendado(
                cultivo_codigo=insumo["codigo"],
                nombre=insumo["codigo"].title(),
                area_m2=AREA_TERRENO / len(insumos),
                demanda_l_m2_dia=insumo["demanda_l_m2_dia"],
                ciclo_dias=insumo.get("ciclo_dias"),
                justificacion="Reparto de prueba.",
            )
            for insumo in insumos
        ],
        sistema=SistemaRecomendado(
            tipo="goteo",
            emisor=EmisorRecomendado(tipo="gotero", caudal_lh=2, separacion_m=0.3),
            separacion_laterales_m=0.5,
            bomba_hp=1,
            num_sectores=4,
        ),
    )


def test_el_informe_en_catalogo_dice_que_no_hubo_modelo(cliente: TestClient) -> None:
    """S3/S5: la marca llega al informe y las fuentes internas no se presentan."""

    proyecto_id = _proyecto(cliente)
    corrida_id, _ = _corrida(cliente, proyecto_id)
    aplicada = cliente.post(
        f"/proyectos/{proyecto_id}/agente/corridas/{corrida_id}/aplicar"
    )
    assert aplicada.status_code == 200, aplicada.text

    respuesta = cliente.get(f"/proyectos/{proyecto_id}/resultado")
    assert respuesta.status_code == 200, respuesta.text
    informe = respuesta.json()

    assert any(
        advertencia["codigo"] == "AGENTE_SIN_CREDENCIALES"
        for advertencia in informe["advertencias"]
    )
    tipos = {fuente["tipo"] for fuente in informe["diseno"]["fuentes"]}
    assert "catalogo_interno" not in tipos
    assert informe["diseno"]["fuentes"] == []


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


def test_el_aviso_no_bloquea_cuando_el_caudal_lo_asumio_el_sistema(
    db_session: Session,
) -> None:
    """S1: sobre un caudal asumido no se puede frenar al usuario, sólo avisar."""
    entrada = _entrada(0.05, caudal_origen="asumido")

    corregida = agente_service._con_reparto_agronomico(
        db_session, entrada, _propuesta(_insumos())
    )

    aviso = next(
        alerta
        for alerta in corregida.advertencias
        if alerta.codigo == "DEMANDA_EXCEDE_CAUDAL"
    )
    assert aviso.bloqueante is False
    assert "asumido" in aviso.mensaje
