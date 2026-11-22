"""Probes del verificador para S1-S6 (handoff; no forman parte del candidato).

Los dos primeros fallan hoy: son los hallazgos del informe de verificación.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.main import app
from app.models.agente import AgenteCorrida, AgenteRecomendacion
from app.models.catalogo import Cultivo, Suelo
from app.models.usuario import Usuario
from tests.conftest import create_user

# Cóncava realista: dos brazos unidos por una columna, con el hueco más ancho que una franja.
C_SHAPE = [(0.0, 0.0), (30.0, 0.0), (30.0, 10.0), (10.0, 10.0),
           (10.0, 20.0), (30.0, 20.0), (30.0, 30.0), (0.0, 30.0)]
TRAPECIO = [(0.0, 40.0), (60.0, 40.0), (60.0, 20.0), (30.0, 0.0), (0.0, 0.0)]
CULTIVOS = ("papa", "lechuga", "maiz", "tomate", "zanahoria")
CONFIG = {
    "fuente_agua": "pozo", "bomba_hp": 1, "diametro_principal_mm": 32,
    "emisor": {"tipo": "gotero", "caudal_lh": 2, "separacion_m": 0.3},
    "separacion_laterales_m": 0.5, "orientacion": "E-O",
    "punto_conexion": {"x": 0, "y": 0}, "num_sectores": 8,
}


def _area(anillo: list[tuple[float, float]]) -> float:
    return abs(sum(
        anillo[i][0] * anillo[(i + 1) % len(anillo)][1]
        - anillo[(i + 1) % len(anillo)][0] * anillo[i][1]
        for i in range(len(anillo))
    )) / 2.0


def _dentro(punto, anillo, tolerancia: float = 1e-3) -> bool:
    """Dentro del polígono con 1 mm de borde (los vértices se guardan a 0,1 mm)."""
    x, y = punto
    dentro = False
    for i, a in enumerate(anillo):
        b = anillo[(i + 1) % len(anillo)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        largo = dx * dx + dy * dy
        if largo <= 1e-18:
            t = 0.0
        else:
            t = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / largo))
        if ((x - a[0] - dx * t) ** 2 + (y - a[1] - dy * t) ** 2) ** 0.5 <= tolerancia:
            return True
        if (a[1] > y) != (b[1] > y) and a[0] + (y - a[1]) * dx / dy > x:
            dentro = not dentro
    return dentro


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="verif@example.com")


@pytest.fixture()
def cliente(client: TestClient, usuario: Usuario) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_current_user] = lambda: usuario
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def catalogo(db_session: Session) -> None:
    db_session.add_all([
        Cultivo(codigo=c, nombre=c.title(), icono="X", color="#4CAF50",
                demanda_agua_l_m2_dia=2.0, ciclo_dias=90, activo=True)
        for c in CULTIVOS
    ])
    db_session.add(Suelo(codigo="franco", nombre="Franco", infiltracion_mm_h=12.0))
    db_session.commit()


def _proyecto(cliente: TestClient, vertices) -> str:
    pid = cliente.post("/proyectos", json={"nombre": "V"}).json()["id"]
    r = cliente.put(
        f"/proyectos/{pid}/terreno",
        json={"nombre_parcela": "P", "forma": "poligono",
              "vertices": [{"x": x, "y": y} for x, y in vertices],
              "suelo_codigo": "franco", "pendiente_pct": 2, "fuente_agua": "pozo"},
    )
    assert r.status_code == 200, r.text
    return pid


def _diseno(cliente: TestClient, pid: str, num_sectores: int = 8) -> dict:
    for codigo in CULTIVOS:
        assert cliente.post(
            f"/proyectos/{pid}/cultivos",
            json={"cultivo_codigo": codigo, "modo": "porcentaje", "porcentaje": 20},
        ).status_code == 201
    assert cliente.put(
        f"/proyectos/{pid}/riego", json=dict(CONFIG, num_sectores=num_sectores)
    ).status_code == 200
    r = cliente.post(f"/proyectos/{pid}/riego/generar")
    assert r.status_code == 200, r.text
    return r.json()


def test_s3_concava_los_nodos_y_tramos_quedan_dentro_del_terreno(cliente):
    """S3/S4: en un terreno en C la válvula y el secundario caen en el hueco."""
    pid = _proyecto(cliente, C_SHAPE)
    diseno = _diseno(cliente, pid)

    fuera = [
        (n["tipo"], n["geometria"]) for n in diseno["red"]["nodos"]
        if not _dentro((n["geometria"]["x"], n["geometria"]["y"]), C_SHAPE)
    ]
    assert fuera == []
    assert [
        (t["tipo"], p) for t in diseno["red"]["tramos"] for p in t["puntos"]
        if not _dentro(tuple(p), C_SHAPE)
    ] == []


def test_s1_las_franjas_de_un_triangulo_agudo_cierran_la_cuota(cliente):
    """S1: franjas que se afinan hasta el vértice no caen al polígono entero."""
    pid = _proyecto(cliente, [(0.0, 0.0), (60.0, 0.0), (0.0, 40.0)])
    diseno = _diseno(cliente, pid)
    areas = [s["area_m2"] for s in diseno["sectores"]]
    assert areas == pytest.approx([150.0] * 8, abs=0.01)
    assert sum(areas) <= 1200.05


def test_s2_el_bloque_que_no_cabe_se_rechaza_sin_tocar_el_balance(cliente):
    """S2: asignado el 100 %, otro bloque da 422 y no cambia nada."""
    pid = _proyecto(cliente, TRAPECIO)
    _diseno(cliente, pid)
    antes = cliente.get(f"/proyectos/{pid}/cultivos/balance").json()
    r = cliente.post(f"/proyectos/{pid}/cultivos",
                     json={"cultivo_codigo": "papa", "modo": "porcentaje",
                           "porcentaje": 20})
    assert r.status_code == 422
    assert r.json()["detail"] == "No queda superficie libre para asignar otro bloque"
    assert cliente.get(f"/proyectos/{pid}/cultivos/balance").json() == antes


def test_s5_el_filtro_no_descarta_una_recomendacion_legitima(
    cliente, db_session, usuario
):
    """S5: una recomendación real que nombra la siembra elegida no debe desaparecer."""
    import uuid

    from app.services import agente as agente_svc

    pid = _proyecto(cliente, TRAPECIO)
    corrida = AgenteCorrida(
        proyecto_id=uuid.UUID(pid), usuario_id=usuario.id, estado="ok",
        entrada={}, salida={}, intake_hash="0" * 64, motor_version="1.0.0",
        prompt_version="1.0.0",
    )
    db_session.add(corrida)
    db_session.commit()
    legitima = {
        "titulo": "Adelantar la siembra del maíz",
        "detalle": "La siembra elegida (2026-11-21) cae fuera de la ventana térmica.",
        "justificacion": "El maíz necesita 12 °C de suelo.",
    }
    db_session.add(AgenteRecomendacion(
        corrida_id=corrida.id, tipo="distribucion", payload=legitima,
        justificacion=legitima["justificacion"], aplicada=False,
    ))
    db_session.commit()

    recomendaciones, _ = agente_svc._recomendaciones_y_advertencias(
        db_session, corrida, None)
    assert [r.titulo for r in recomendaciones] == ["Adelantar la siembra del maíz"]
