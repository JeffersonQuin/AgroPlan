"""Resultado del paso 4: cifras del motor, calendario, materiales, ajustes, S7 y S9.

Cubre S3 (el motor se ajusta a las cifras del agente y el ajuste se muestra), S9 (el
resultado expone presión, caudal por sector, tiempo de riego, autonomía, demanda pico,
calendario, cómputo y eficiencia) y S7 (recomendaciones y fuentes persistidas por fin
se leen en el informe).
"""

import uuid
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.main import app
from app.models.agente import AgenteCorrida, AgenteFuente, AgenteRecomendacion
from app.models.catalogo import Cultivo, Suelo
from app.models.proyecto import Proyecto
from app.models.usuario import Usuario
from app.services import agente as agente_service
from tests.conftest import create_user

ENTRADA = {
    "productos": [{"nombre": "Papa", "prioridad": 1}],
    "area_m2": 200.0,
    "suelo_codigo": "franco",
    "fuente_agua": "pozo",
    "caudal_efectivo_m3h": 1.5,
    "caudal_origen": "asumido",
    "zona": "Cuyo",
    "pendiente_pct": 2.0,
}


def _salida(*, cifras: dict | None = None, materiales: list[dict] | None = None,
            recomendaciones: list[dict] | None = None, area_m2: float = 200.0,
            turnos: list[dict] | None = None) -> dict:
    return {
        "cultivos": [
            {
                "cultivo_codigo": "papa",
                "nombre": "Papa",
                "color": "#8D6E63",
                "area_m2": area_m2,
                "demanda_l_m2_dia": 2.0,
                "ciclo_dias": 120,
                "siembra_sugerida": "2026-05-01",
                "cosecha_sugerida": "2026-08-29",
                "justificacion": "Es el cultivo que pidió el usuario.",
                "imagen_url": "https://fichas.example/papa.jpg",
            }
        ],
        "sistema": {
            "tipo": "goteo",
            "emisor": {"tipo": "gotero", "caudal_lh": 2.0, "separacion_m": 0.3},
            "separacion_laterales_m": 0.5,
            "bomba_hp": 1.0,
            "num_sectores": 1,
        },
        "cifras": cifras if cifras is not None else {"turnos": turnos or []},
        "materiales": materiales or [],
        "recomendaciones": recomendaciones or [],
        "advertencias": [],
    }


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="resultado4@example.com")


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


def _proyecto(cliente: TestClient) -> str:
    pid = cliente.post("/proyectos", json={"nombre": "P", "zona": "Cuyo"}).json()["id"]
    terreno = cliente.put(
        f"/proyectos/{pid}/terreno",
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
        f"/proyectos/{pid}/cultivos",
        json={"cultivo_codigo": "papa", "modo": "porcentaje", "porcentaje": 100},
    )
    assert bloque.status_code == 201, bloque.text
    return pid


def _corrida(pid: str, db_session: Session, salida: dict, *, estado: str = "ok",
             con_fuentes: bool = False, con_recomendaciones: bool = False,
             restricciones: dict | None = None) -> AgenteCorrida:
    entrada = dict(ENTRADA, proyecto_id=pid)
    if restricciones is not None:
        entrada["restricciones"] = restricciones
    corrida = AgenteCorrida(
        proyecto_id=uuid.UUID(pid),
        usuario_id=db_session.get(Proyecto, uuid.UUID(pid)).usuario_id,
        estado=estado,
        entrada=entrada,
        salida=salida,
        intake_hash=f"hash-{uuid.uuid4()}",
        motor_version="m1",
        prompt_version="v1",
    )
    db_session.add(corrida)
    db_session.commit()

    if con_fuentes:
        db_session.add(
            AgenteFuente(
                corrida_id=corrida.id,
                tipo="web",
                titulo="Precio de tubería",
                url="https://precios.example/tuberia",
                fragmento="PVC 32 mm a 8 Bs/m",
                recuperado_en=datetime.now(timezone.utc),
            )
        )
    if con_recomendaciones:
        db_session.add(
            AgenteRecomendacion(
                corrida_id=corrida.id,
                tipo="sistema_riego",
                payload={"tipo": "goteo", "bomba_hp": 1},
                justificacion="Caudal suficiente para goteo.",
                aplicada=False,
            )
        )
    db_session.commit()
    return corrida


def _aplicar(cliente: TestClient, pid: str, corrida_id: uuid.UUID) -> dict:
    respuesta = cliente.post(f"/proyectos/{pid}/agente/corridas/{corrida_id}/aplicar")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _campos(ajustes: list[dict]) -> set[str]:
    return {ajuste["campo"] for ajuste in ajustes}


# --------------------------------------------------------------------------- #
# S3 — el motor se ajusta y muestra qué cambió
# --------------------------------------------------------------------------- #


def test_el_resultado_expone_las_cifras_del_motor_y_del_agente(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(
        pid,
        db_session,
        _salida(
            cifras={
                "presion_trabajo_bar": 4.5,
                "eficiencia_pct": 85.0,
                "demanda_pico_l_dia": 100.0,
                "autonomia_dias": 3.0,
                "tiempo_riego_h": 1.0,
            }
        ),
    )

    cuerpo = _aplicar(cliente, pid, corrida.id)
    diseno = cuerpo["diseno"]

    # Cifras del motor: las calcula el determinístico despues de generar la red.
    assert diseno["cifras"]["presion_trabajo_bar"] == pytest.approx(1.5)
    assert diseno["cifras"]["caudal_sector_m3h"] > 0
    assert diseno["cifras"]["tiempo_riego_h"] > 0
    assert diseno["cifras"]["demanda_pico_l_dia"] == pytest.approx(400.0)
    assert diseno["cifras"]["autonomia_dias"] is None

    # Cifras del agente: las que propuso, tal cual, para comparar.
    assert diseno["cifras_agente"]["presion_trabajo_bar"] == pytest.approx(4.5)
    assert diseno["cifras_agente"]["demanda_pico_l_dia"] == pytest.approx(100.0)
    assert diseno["eficiencia_pct"] == pytest.approx(85.0)

    ajustes = {ajuste["campo"]: ajuste for ajuste in diseno["ajustes"]}
    presion = ajustes["presion_trabajo_bar"]
    assert presion["valor_agente"] == "4.5"
    assert presion["valor_motor"] == "1.5"
    assert presion["motivo"]

    demanda = ajustes["demanda_pico_l_dia"]
    assert demanda["valor_agente"] == "100"
    assert demanda["valor_motor"] == "400"


def test_el_motor_registra_el_area_completada_y_el_computo_recalculado(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(
        pid,
        db_session,
        _salida(
            area_m2=300.0,
            materiales=[
                {
                    "rubro": "Tubería principal",
                    "descripcion": "PVC 32 mm",
                    "cantidad": 10.0,
                    "unidad": "m",
                    "precio_unitario_bs": 8.0,
                    "total_bs": 80.0,
                    "fuente_url": "https://precios.example/tuberia",
                }
            ],
        ),
    )

    diseno = _aplicar(cliente, pid, corrida.id)["diseno"]
    campos = _campos(diseno["ajustes"])

    assert "area_m2.papa" in campos
    area = next(a for a in diseno["ajustes"] if a["campo"] == "area_m2.papa")
    assert area["valor_agente"] == "300"
    assert float(area["valor_motor"]) == pytest.approx(200.0, abs=1.0)
    assert area["motivo"]

    assert "computo.tuberia_m" in campos
    tuberia = next(a for a in diseno["ajustes"] if a["campo"] == "computo.tuberia_m")
    assert tuberia["valor_agente"] == "10"
    assert tuberia["valor_motor"] != "10"

    # El bloque materializado trae el área real, no la propuesta.
    bloque = diseno["bloques"][0]
    assert bloque["area_m2"] == pytest.approx(200.0, abs=1.0)
    assert bloque["porcentaje"] == pytest.approx(100.0, abs=0.5)
    assert bloque["demanda_pico_l_dia"] == pytest.approx(400.0, abs=1.0)


def test_los_turnos_fuera_de_rango_quedan_como_ajuste_de_sectores(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(
        pid,
        db_session,
        _salida(
            cifras={
                "turnos": [
                    {"sector": numero, "horas": 1.0, "caudal_lh": 500.0}
                    for numero in range(1, 7)
                ]
            }
        ),
    )

    diseno = _aplicar(cliente, pid, corrida.id)["diseno"]
    ajuste = next(a for a in diseno["ajustes"] if a["campo"] == "sectores")
    assert ajuste["valor_agente"] == "6"
    assert ajuste["valor_motor"] == str(len(diseno["sectores"]))
    assert ajuste["motivo"]


def test_sin_cifras_del_agente_no_hay_ajuste_inventado(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(pid, db_session, _salida(), estado="ok")

    diseno = _aplicar(cliente, pid, corrida.id)["diseno"]

    assert diseno["ajustes"] == []
    assert diseno["cifras_agente"]["presion_trabajo_bar"] is None
    assert diseno["cifras_agente"]["eficiencia_pct"] is None
    assert diseno["eficiencia_pct"] is None
    # El motor sigue informando lo suyo.
    assert diseno["cifras"]["presion_trabajo_bar"] is not None


# --------------------------------------------------------------------------- #
# S9 — bloque, calendario y materiales del informe
# --------------------------------------------------------------------------- #


def test_bloques_calendario_y_materiales_llegan_al_resultado(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(
        pid,
        db_session,
        _salida(
            materiales=[
                {
                    "rubro": "Tanque",
                    "descripcion": "Tanque de 5000 L",
                    "cantidad": 1.0,
                    "unidad": "u",
                    "moneda": "BOB",
                    "precio_unitario_bs": 3500.0,
                    "total_bs": 3500.0,
                    "fuente_url": "https://precios.example/tanque",
                }
            ]
        ),
    )

    diseno = _aplicar(cliente, pid, corrida.id)["diseno"]

    bloque = diseno["bloques"][0]
    assert bloque["cultivo_codigo"] == "papa"
    assert bloque["color"] == "#8D6E63"
    assert bloque["ciclo_dias"] == 120
    assert bloque["kc"] == pytest.approx(1.15)
    assert bloque["siembra"] == "2026-05-01"
    assert bloque["cosecha"] == "2026-08-29"
    assert bloque["imagen_url"] == "https://fichas.example/papa.jpg"

    assert len(diseno["calendario"]) == 1
    calendario = diseno["calendario"][0]
    assert calendario["bloque_id"] == bloque["id"]
    assert calendario["siembra"] == "2026-05-01"
    assert calendario["cosecha"] == "2026-08-29"

    assert len(diseno["materiales"]) == 1
    material = diseno["materiales"][0]
    assert material["rubro"] == "Tanque"
    assert material["precio_unitario_bs"] == pytest.approx(3500.0)
    assert material["moneda"] == "BOB"
    assert material["fuente_url"] == "https://precios.example/tanque"


# --------------------------------------------------------------------------- #
# S7 — recomendaciones y fuentes persistidas se leen en el informe
# --------------------------------------------------------------------------- #


def test_el_informe_lee_recomendaciones_y_fuentes_de_la_corrida(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(
        pid,
        db_session,
        _salida(
            recomendaciones=[
                {
                    "titulo": "Regar de noche",
                    "detalle": "Reduce la evaporación.",
                    "justificacion": "El suelo franco retiene bien el agua.",
                }
            ]
        ),
        con_fuentes=True,
        con_recomendaciones=True,
    )

    diseno = _aplicar(cliente, pid, corrida.id)["diseno"]

    final = next(r for r in diseno["recomendaciones"] if r["tipo"] == "final")
    assert final["titulo"] == "Regar de noche"
    assert final["detalle"] == "Reduce la evaporación."
    assert final["justificacion"] == "El suelo franco retiene bien el agua."
    assert final["aplicada"] is None

    persistida = next(
        r for r in diseno["recomendaciones"] if r["tipo"] == "sistema_riego"
    )
    assert persistida["justificacion"] == "Caudal suficiente para goteo."
    assert persistida["aplicada"] is True

    assert len(diseno["fuentes"]) == 1
    assert diseno["fuentes"][0]["url"] == "https://precios.example/tuberia"


def test_el_endpoint_de_resultado_expone_lo_mismo(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(
        pid,
        db_session,
        _salida(cifras={"presion_trabajo_bar": 4.5}),
        con_fuentes=True,
    )
    _aplicar(cliente, pid, corrida.id)

    cuerpo = cliente.get(f"/proyectos/{pid}/resultado")
    assert cuerpo.status_code == 200, cuerpo.text
    diseno = cuerpo.json()["diseno"]
    assert diseno["cifras_agente"]["presion_trabajo_bar"] == pytest.approx(4.5)
    assert "presion_trabajo_bar" in _campos(diseno["ajustes"])
    assert diseno["calendario"]
    assert diseno["fuentes"]


def test_la_corrida_expone_sus_recomendaciones_persistidas(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(pid, db_session, _salida(), con_recomendaciones=True)

    detalle = cliente.get(f"/proyectos/{pid}/agente/corridas/{corrida.id}")
    assert detalle.status_code == 200, detalle.text
    filas = detalle.json()["recomendaciones"]
    assert len(filas) == 1
    assert filas[0]["tipo"] == "sistema_riego"
    assert filas[0]["aplicada"] is False


def test_calendario_no_inventa_fechas_ausentes(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    """Un bloque sin siembra ni cosecha se informa en null, nunca con un cero."""
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    salida = _salida()
    for cultivo in salida["cultivos"]:
        cultivo.pop("siembra_sugerida")
        cultivo.pop("cosecha_sugerida")
    corrida = _corrida(pid, db_session, salida)

    diseno = _aplicar(cliente, pid, corrida.id)["diseno"]
    assert diseno["bloques"][0]["siembra"] is None
    assert diseno["calendario"][0]["siembra"] is None
    assert diseno["calendario"][0]["cosecha"] is None
    # Una fecha no informada no genera un ajuste.
    assert "siembra" not in _campos(diseno["ajustes"])


# --------------------------------------------------------------------------- #
# Correcciones de la verificación: caudal real, turnos, materiales y tolerancia
# --------------------------------------------------------------------------- #


def _salida_con_sectores(num_sectores: int, *, turnos: list[dict] | None = None,
                          presion: float | None = None) -> dict:
    salida = _salida(cifras={"turnos": turnos or []})
    salida["sistema"]["num_sectores"] = num_sectores
    if presion is not None:
        salida["cifras"]["presion_trabajo_bar"] = presion
    return salida


def test_caudal_por_sector_coincide_con_la_red_generada(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    """La cifra del motor sale de la red real, no del caudal efectivo del preview."""
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(pid, db_session, _salida())

    diseno = _aplicar(cliente, pid, corrida.id)["diseno"]

    assert len(diseno["sectores"]) == 1
    assert diseno["cifras"]["caudal_sector_m3h"] == pytest.approx(
        diseno["sectores"][0]["caudal_m3h"]
    )


def test_cada_turno_se_compara_contra_su_sector(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(
        pid,
        db_session,
        _salida_con_sectores(
            2,
            turnos=[
                {"sector": 1, "horas": 2.0, "caudal_lh": 1500.0},
                {"sector": 2, "horas": 2.0, "caudal_lh": 6500.0},
            ],
        ),
    )

    diseno = _aplicar(cliente, pid, corrida.id)["diseno"]
    sectores = {sector["numero"]: sector for sector in diseno["sectores"]}
    ajustes = {ajuste["campo"]: ajuste for ajuste in diseno["ajustes"]}

    for numero, caudal_lh in ((1, 1500.0), (2, 6500.0)):
        ajuste = ajustes[f"caudal_sector_lh.{numero}"]
        assert ajuste["valor_agente"] == f"{caudal_lh:g}"
        assert float(ajuste["valor_motor"]) == pytest.approx(
            sectores[numero]["caudal_m3h"] * 1000.0
        )
        assert ajuste["motivo"]

    # Ninguno de los dos turnos quedó sin comparar.
    assert sum(1 for campo in ajustes if campo.startswith("caudal_sector_lh")) == 2


def test_turnos_y_sectores_que_no_coinciden_generan_ajuste(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(
        pid,
        db_session,
        _salida_con_sectores(
            2,
            # El bloque (centroide a la derecha) cae en el sector 2, que es el de
            # 200 m² y 2666 L/h; el sector 1 queda con la franja vacía de 100 m².
            turnos=[
                {"sector": 2, "horas": 2.0, "caudal_lh": 2666.0},
                {"sector": 5, "horas": 2.0, "caudal_lh": 900.0},
            ],
        ),
    )

    diseno = _aplicar(cliente, pid, corrida.id)["diseno"]
    ajustes = {ajuste["campo"]: ajuste for ajuste in diseno["ajustes"]}

    # Un turno de un sector que la red no generó.
    inexistente = ajustes["caudal_sector_lh.5"]
    assert inexistente["valor_agente"] == "900"
    assert inexistente["valor_motor"] is None
    assert inexistente["motivo"]

    # Un sector de la red que el agente no cubrió con ningún turno.
    sin_turno = ajustes["caudal_sector_lh.1"]
    assert sin_turno["valor_agente"] is None
    assert sin_turno["valor_motor"] is not None
    assert sin_turno["motivo"]

    # El sector 2 sí coincide con la red: no genera ajuste de caudal.
    assert "caudal_sector_lh.2" not in ajustes


def test_los_materiales_normalizan_rubro_y_unidad(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(
        pid,
        db_session,
        _salida(
            materiales=[
                {
                    "rubro": "Válvulas",
                    "descripcion": "Válvula de sector",
                    "cantidad": 6.0,
                    "unidad": "u",
                    "precio_unitario_bs": 45.0,
                    "total_bs": 270.0,
                },
                {
                    "rubro": "Tubería principal",
                    "descripcion": "PVC 32 mm",
                    "cantidad": 5.0,
                    "unidad": "Metro lineal",
                    "precio_unitario_bs": 8.0,
                    "total_bs": 40.0,
                },
                {
                    "rubro": "Tanque",
                    "descripcion": "Tanque de 5000 L",
                    "cantidad": 2.0,
                    "unidad": "u",
                    "precio_unitario_bs": 3500.0,
                    "total_bs": 7000.0,
                },
            ]
        ),
    )

    diseno = _aplicar(cliente, pid, corrida.id)["diseno"]
    ajustes = {ajuste["campo"]: ajuste for ajuste in diseno["ajustes"]}
    computo = diseno["computo"]

    assert ajustes["computo.valvulas_u"]["valor_agente"] == "6"
    assert ajustes["computo.valvulas_u"]["valor_motor"] == str(computo["valvulas_u"])
    assert ajustes["computo.tuberia_m"]["valor_agente"] == "5"
    assert ajustes["computo.tuberia_m"]["valor_motor"] == f"{computo['tuberia_m']:g}"

    # Tanque, bomba y conexiones no los computa el motor: no se contrastan.
    assert not any("tanque" in campo.lower() for campo in ajustes)


def test_el_motivo_de_sectores_dice_lo_que_paso(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(
        pid,
        db_session,
        _salida_con_sectores(
            1,
            turnos=[
                {"sector": 1, "horas": 1.0, "caudal_lh": 2666.0},
                {"sector": 2, "horas": 1.0, "caudal_lh": 2666.0},
                {"sector": 3, "horas": 1.0, "caudal_lh": 2666.0},
            ],
        ),
    )

    diseno = _aplicar(cliente, pid, corrida.id)["diseno"]
    ajuste = next(a for a in diseno["ajustes"] if a["campo"] == "sectores")

    assert ajuste["valor_agente"] == "3"
    assert ajuste["valor_motor"] == str(len(diseno["sectores"]))
    # El motor no acotó nada al rango 1..8: usó el num_sectores de la corrida.
    assert "1 a 8" not in ajuste["motivo"]
    assert "3" in ajuste["motivo"]
    assert "1" in ajuste["motivo"]


def test_el_borde_de_la_tolerancia_no_es_un_ajuste() -> None:
    """1.5 vs 1.55 es el borde exacto de 0.05: no cuenta; 1.56 sí."""

    assert agente_service._difiere(1.5, 1.55, 0.05) is False
    assert agente_service._difiere(1.5, 1.56, 0.05) is True


# --------------------------------------------------------------------------- #
# S6 — el informe compara el cómputo contra el presupuesto del paso 3
# --------------------------------------------------------------------------- #

MATERIALES_CORTOS = [
    {
        "rubro": "Tubería principal",
        "descripcion": "PVC 32 mm",
        "cantidad": 10.0,
        "unidad": "m",
        "precio_unitario_bs": 8.0,
        "total_bs": 80.0,
        "fuente_url": "https://precios.example/tuberia",
    },
    {
        # Sin precio: no suma al cómputo y no se cuenta como cero.
        "rubro": "Filtro de anillas",
        "descripcion": "Filtro 2 pulgadas",
        "cantidad": 1.0,
        "unidad": "u",
        "precio_unitario_bs": None,
        "total_bs": None,
    },
]


def _alertas(cuerpo: dict) -> list[dict]:
    return [
        alerta
        for alerta in cuerpo["advertencias"]
        if alerta["codigo"] == "PRESUPUESTO_EXCEDIDO"
    ]


def test_el_informe_muestra_el_computo_dentro_del_presupuesto(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(
        pid,
        db_session,
        _salida(materiales=MATERIALES_CORTOS),
        restricciones={"presupuesto_bs": 1000.0},
    )

    cuerpo = _aplicar(cliente, pid, corrida.id)
    diseno = cuerpo["diseno"]

    assert diseno["presupuesto_bs"] == pytest.approx(1000.0)
    assert diseno["costo_total_bs"] == pytest.approx(80.0)
    assert diseno["presupuesto_excedido"] is False
    assert _alertas(cuerpo) == []


def test_el_informe_advierte_cuando_el_computo_supera_el_presupuesto(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(
        pid,
        db_session,
        _salida(
            materiales=[
                {
                    "rubro": "Tanque",
                    "descripcion": "Tanque de 5000 L",
                    "cantidad": 1.0,
                    "unidad": "u",
                    "precio_unitario_bs": 1500.0,
                    "total_bs": 1500.0,
                    "fuente_url": "https://precios.example/tanque",
                }
            ]
        ),
        restricciones={"presupuesto_bs": 1000.0},
    )

    cuerpo = _aplicar(cliente, pid, corrida.id)
    diseno = cuerpo["diseno"]

    assert diseno["presupuesto_bs"] == pytest.approx(1000.0)
    assert diseno["costo_total_bs"] == pytest.approx(1500.0)
    assert diseno["presupuesto_excedido"] is True

    alertas = _alertas(cuerpo)
    assert len(alertas) == 1
    assert "1500.00" in alertas[0]["mensaje"]
    assert "1000.00" in alertas[0]["mensaje"]
    assert "500.00" in alertas[0]["mensaje"]
    assert alertas[0]["campo"] == "presupuesto_bs"
    # No se recortó ningún material ni se cambió el presupuesto.
    assert diseno["materiales"][0]["total_bs"] == pytest.approx(1500.0)


def test_sin_presupuesto_no_hay_comparacion_inventada(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    corrida = _corrida(pid, db_session, _salida(materiales=MATERIALES_CORTOS))

    cuerpo = _aplicar(cliente, pid, corrida.id)
    diseno = cuerpo["diseno"]

    assert diseno["presupuesto_bs"] is None
    assert diseno["costo_total_bs"] == pytest.approx(80.0)
    assert diseno["presupuesto_excedido"] is None
    assert _alertas(cuerpo) == []


def test_la_advertencia_del_informe_reemplaza_la_de_la_corrida(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    """S6: el aviso que se muestra trae los montos, no el texto escueto de la corrida."""
    pid = _proyecto(cliente_autenticado)
    salida = _salida(
        materiales=[
            {
                "rubro": "Tanque",
                "descripcion": "Tanque 5.000 L",
                "cantidad": 1.0,
                "unidad": "u",
                "precio_unitario_bs": 1500.0,
                "total_bs": 1500.0,
            }
        ]
    )
    salida["advertencias"] = [
        {"codigo": "PRESUPUESTO_EXCEDIDO", "mensaje": "El cómputo supera el presupuesto."}
    ]
    corrida = _corrida(
        pid, db_session, salida, restricciones={"energia": "solar", "presupuesto_bs": 1000}
    )
    resultado = _aplicar(cliente_autenticado, pid, corrida.id)
    diseno = resultado["diseno"]

    assert diseno["presupuesto_excedido"] is True
    avisos = [
        alerta
        for alerta in resultado["advertencias"]
        if alerta["codigo"] == "PRESUPUESTO_EXCEDIDO"
    ]
    assert len(avisos) == 1
    assert "500.00" in avisos[0]["mensaje"]
    assert avisos[0]["campo"] == "presupuesto_bs"
