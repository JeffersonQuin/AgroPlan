"""Sectores, zonas de cultivo y red de riego dentro del polígono real (S1-S3).

El trapecio del usuario es la referencia: 2100 m² con base de 60 m y altura de 40 m.
Antes los sectores eran franjas de la caja envolvente (7,5 × 40 = 300 m²) y las
zonas de cultivo bandas de 60 × 7 que se salían del terreno. Con el recorte, cada
franja sigue el contorno y la red no dibuja nada afuera.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.main import app
from app.models.catalogo import Cultivo, Suelo
from app.models.usuario import Usuario
from app.services import geometria
from tests.conftest import create_user

TRAPECIO = [
    {"x": 0, "y": 40},
    {"x": 60, "y": 40},
    {"x": 60, "y": 20},
    {"x": 30, "y": 0},
    {"x": 0, "y": 0},
]
ANILLO_TRAPECIO = [(0.0, 40.0), (60.0, 40.0), (60.0, 20.0), (30.0, 0.0), (0.0, 0.0)]
AREA_TRAPECIO = 2100.0

RECTANGULO = [
    {"x": 0, "y": 0},
    {"x": 60, "y": 0},
    {"x": 60, "y": 40},
    {"x": 0, "y": 40},
]

CULTIVOS = ("papa", "lechuga", "maiz", "tomate", "zanahoria")

# Parámetros del sistema del proyecto real: goteo de 2 L/h cada 0,3 m, laterales
# cada 0,5 m, orientación E-O (laterales horizontales) y 8 sectores.
CONFIG = {
    "fuente_agua": "pozo",
    "bomba_hp": 1,
    "diametro_principal_mm": 32,
    "emisor": {"tipo": "gotero", "caudal_lh": 2, "separacion_m": 0.3},
    "separacion_laterales_m": 0.5,
    "orientacion": "E-O",
    "punto_conexion": {"x": 0, "y": 0},
    "num_sectores": 8,
}


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="geometria@example.com")


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


@pytest.fixture(autouse=True)
def catalogo(db_session: Session) -> None:
    db_session.add_all(
        [
            Cultivo(
                codigo=codigo,
                nombre=codigo.title(),
                icono="X",
                color="#4CAF50",
                demanda_agua_l_m2_dia=2.0,
                ciclo_dias=90,
                activo=True,
            )
            for codigo in CULTIVOS
        ]
    )
    db_session.add(Suelo(codigo="franco", nombre="Franco", infiltracion_mm_h=12.0))
    db_session.commit()


def _proyecto(cliente: TestClient, vertices: list[dict], forma: str) -> str:
    proyecto = cliente.post("/proyectos", json={"nombre": "Geometría"})
    assert proyecto.status_code == 201, proyecto.text
    proyecto_id = proyecto.json()["id"]
    terreno = cliente.put(
        f"/proyectos/{proyecto_id}/terreno",
        json={
            "nombre_parcela": "La Parcela",
            "forma": forma,
            "vertices": vertices,
            "suelo_codigo": "franco",
            "pendiente_pct": 2,
            "fuente_agua": "pozo",
        },
    )
    assert terreno.status_code == 200, terreno.text
    return proyecto_id


def _bloques(cliente: TestClient, proyecto_id: str, porcentaje: float = 20) -> list[dict]:
    bloques = []
    for codigo in CULTIVOS:
        alta = cliente.post(
            f"/proyectos/{proyecto_id}/cultivos",
            json={
                "cultivo_codigo": codigo,
                "modo": "porcentaje",
                "porcentaje": porcentaje,
            },
        )
        assert alta.status_code == 201, alta.text
        bloques.append(alta.json()["bloque"])
    return bloques


def _diseno(cliente: TestClient, proyecto_id: str) -> dict:
    config = cliente.put(f"/proyectos/{proyecto_id}/riego", json=CONFIG)
    assert config.status_code == 200, config.text
    generado = cliente.post(f"/proyectos/{proyecto_id}/riego/generar")
    assert generado.status_code == 200, generado.text
    return generado.json()


def _anillo(poligono: dict) -> list[tuple[float, float]]:
    return [(float(x), float(y)) for x, y in poligono["anillo"]]


def _area_anillo(anillo: list[tuple[float, float]]) -> float:
    return geometria.area_poligono(anillo)


def _dentro(punto, anillo=ANILLO_TRAPECIO) -> bool:
    """Dentro del terreno, tolerando el redondeo a 4 decimales de los polígonos.

    Las coordenadas persistidas se redondean a 0,1 mm, así que un vértice que cae
    justo sobre el borde inclinado puede quedar 1e-5 m afuera: se tolera 1 mm de
    borde, que no alcanza para dejar pasar un punto realmente fuera del terreno.
    """

    return geometria.punto_en_poligono(tuple(punto), anillo, tolerancia=1e-3)


# --------------------------------------------------------------------------- #
# S1 — sectores dentro del polígono, por área usable
# --------------------------------------------------------------------------- #


def test_el_area_de_cada_sector_es_la_del_trapecio_recortado(cliente: TestClient) -> None:
    proyecto_id = _proyecto(cliente, TRAPECIO, "trapecio")
    _bloques(cliente, proyecto_id)

    diseno = _diseno(cliente, proyecto_id)
    sectores = diseno["sectores"]

    assert len(sectores) == 8
    cuota = AREA_TRAPECIO / len(sectores)
    for sector in sectores:
        anillo = _anillo(sector["poligono"])
        assert _area_anillo(anillo) == pytest.approx(sector["area_m2"], abs=0.01)
        assert sector["area_m2"] == pytest.approx(cuota, abs=0.01)
        assert sector["area_m2"] <= cuota + 1e-6
    assert sum(sector["area_m2"] for sector in sectores) <= AREA_TRAPECIO + 1e-6
    assert sum(sector["area_m2"] for sector in sectores) == pytest.approx(AREA_TRAPECIO)
    # El reparto por área usable ya no inventa el aviso de sectores que sobran.
    assert "sectores_exceden_terreno" not in {
        advertencia["codigo"] for advertencia in diseno["advertencias"]
    }


def test_ningun_vertice_de_sector_cae_fuera_del_trapecio(cliente: TestClient) -> None:
    proyecto_id = _proyecto(cliente, TRAPECIO, "trapecio")
    _bloques(cliente, proyecto_id)

    sectores = _diseno(cliente, proyecto_id)["sectores"]

    fuera = [
        (sector["numero"], vertice)
        for sector in sectores
        for vertice in _anillo(sector["poligono"])
        if not _dentro(vertice)
    ]
    assert fuera == []
    # Y las franjas siguen el trapecio: la última no es un rectángulo de 40 m de alto.
    ultima = _anillo(sectores[-1]["poligono"])
    assert min(y for _, y in ultima) > 1.0


def test_los_goteros_y_el_caudal_salen_del_area_real(cliente: TestClient) -> None:
    proyecto_id = _proyecto(cliente, TRAPECIO, "trapecio")
    _bloques(cliente, proyecto_id)

    diseno = _diseno(cliente, proyecto_id)
    sectores = diseno["sectores"]

    for sector in sectores:
        esperado = round(sector["area_m2"] / (0.3 * 0.5))
        assert sector["num_goteros"] == esperado
        assert sector["caudal_m3h"] == pytest.approx(esperado * 2 / 1000, abs=0.001)
    assert diseno["computo"]["goteros_u"] == 14_000  # 2100 m² / 0,15 m² por gotero


# --------------------------------------------------------------------------- #
# S2 — zonas de cultivo dentro del polígono que cubren el terreno
# --------------------------------------------------------------------------- #


def test_las_zonas_de_cultivo_siguen_el_trapecio_y_cubren_el_terreno(
    cliente: TestClient,
) -> None:
    proyecto_id = _proyecto(cliente, TRAPECIO, "trapecio")

    bloques = _bloques(cliente, proyecto_id)
    anillos = [_anillo(bloque["poligono"]) for bloque in bloques]

    assert sum(bloque["area_m2"] for bloque in bloques) == pytest.approx(
        AREA_TRAPECIO, abs=0.05
    )
    for bloque, anillo in zip(bloques, anillos):
        assert bloque["area_m2"] == pytest.approx(_area_anillo(anillo), abs=0.01)
        assert all(_dentro(vertice) for vertice in anillo)

    # Las zonas que tocan la diagonal del trapecio la acompañan: heredan un vértice
    # sobre el borde inclinado en vez de cortar contra la caja envolvente de 60 m.
    def en_la_diagonal(punto: tuple[float, float]) -> bool:
        x, y = punto
        return 0.0 < y < 20.0 and abs(x - (30.0 + 1.5 * y)) <= 1e-2

    inclinadas = [
        anillo for anillo in anillos if any(en_la_diagonal(p) for p in anillo)
    ]
    assert len(inclinadas) >= 2
    for anillo in inclinadas:
        assert len({round(x, 6) for x, _ in anillo}) >= 3
        assert any(0.0 < x < 60.0 for x, _ in anillo)

    balance = cliente.get(f"/proyectos/{proyecto_id}/cultivos/balance").json()
    assert balance["asignado_m2"] == pytest.approx(AREA_TRAPECIO, abs=0.05)
    assert balance["estado"] == "correcto"


# --------------------------------------------------------------------------- #
# S3 — red y cómputo sobre los sectores reales
# --------------------------------------------------------------------------- #


def test_ningun_tramo_ni_emisor_ni_valvula_queda_fuera_del_trapecio(
    cliente: TestClient,
) -> None:
    proyecto_id = _proyecto(cliente, TRAPECIO, "trapecio")
    _bloques(cliente, proyecto_id)

    red = _diseno(cliente, proyecto_id)["red"]

    fuera_tramos = [
        tramo["id"]
        for tramo in red["tramos"]
        for punto in tramo["puntos"]
        if not _dentro(punto)
    ]
    assert fuera_tramos == []

    fuera_emisores = [
        emisor["tramo_id"]
        for emisor in red["emisores"]
        for punto in emisor["puntos"]
        if not _dentro(punto)
    ]
    assert fuera_emisores == []

    valvulas = [nodo for nodo in red["nodos"] if nodo["tipo"] == "valvula"]
    assert len(valvulas) == 8
    for valvula in valvulas:
        punto = (valvula["geometria"]["x"], valvula["geometria"]["y"])
        assert _dentro(punto)


def test_la_tuberia_sale_de_las_longitudes_recortadas(cliente: TestClient) -> None:
    proyecto_id = _proyecto(cliente, TRAPECIO, "trapecio")
    _bloques(cliente, proyecto_id)

    diseno = _diseno(cliente, proyecto_id)
    tramos = diseno["red"]["tramos"]
    laterales = [tramo for tramo in tramos if tramo["tipo"] == "lateral"]

    assert diseno["computo"]["tuberia_m"] == pytest.approx(
        round(sum(tramo["longitud_m"] for tramo in tramos), 2)
    )
    # Los laterales E-O cubren el área real cada 0,5 m: 2100 / 0,5 = 4200 m.
    assert sum(tramo["longitud_m"] for tramo in laterales) == pytest.approx(
        4200.0, abs=20.0
    )
    # Antes eran 4800 m de laterales (8 sectores × 80 × 7,5 m sobre la caja).
    assert sum(tramo["longitud_m"] for tramo in laterales) < 4800.0
    assert diseno["computo"]["tuberia_m"] < 4956.06


# --------------------------------------------------------------------------- #
# (d) El caso simple no cambia
# --------------------------------------------------------------------------- #


def test_un_terreno_rectangular_conserva_los_sectores_y_la_tuberia_de_hoy(
    cliente: TestClient,
) -> None:
    proyecto_id = _proyecto(cliente, RECTANGULO, "rectangulo")
    _bloques(cliente, proyecto_id)

    diseno = _diseno(cliente, proyecto_id)
    tramos = diseno["red"]["tramos"]
    por_tipo: dict[str, float] = {}
    for tramo in tramos:
        por_tipo[tramo["tipo"]] = por_tipo.get(tramo["tipo"], 0.0) + tramo["longitud_m"]

    # Sectores: las mismas franjas verticales de 7,5 × 40 de siempre.
    for indice, sector in enumerate(diseno["sectores"]):
        anillo = _anillo(sector["poligono"])
        assert _area_anillo(anillo) == pytest.approx(300.0)
        assert sector["area_m2"] == 300.0
        assert min(x for x, _ in anillo) == pytest.approx(7.5 * indice)
        assert max(x for x, _ in anillo) == pytest.approx(7.5 * (indice + 1))
        assert min(y for _, y in anillo) == 0.0
        assert max(y for _, y in anillo) == 40.0

    # Tubería: 8 sectores × 80 laterales × 7,5 m + secundarios + principal.
    assert por_tipo["lateral"] == pytest.approx(4800.0)
    assert len([t for t in tramos if t["tipo"] == "lateral"]) == 640
    assert por_tipo["secundario"] == pytest.approx(120.0)
    assert por_tipo["principal"] == pytest.approx(36.06, abs=0.01)
    assert diseno["computo"]["tuberia_m"] == pytest.approx(4956.06, abs=0.01)
    assert diseno["computo"]["goteros_u"] == 16_000  # 2400 m² / 0,15 m² por gotero
