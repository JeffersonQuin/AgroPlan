"""Caché de precios de materiales (S6, T2 parte B).

El agente investiga precios con fuentes y el backend los guarda en la base para que
otra corrida —de otro usuario— los reutilice sin volver a investigar. Un precio más
viejo que la vigencia no se reutiliza: se vuelve a investigar y el nuevo reemplaza al
viejo, sin duplicar filas. El informe compara el total del cómputo contra el
presupuesto del paso 3 y avisa cuando lo supera.

Todo corre en modo catálogo o con el agente reemplazado por un doble: no se llama al
modelo.
"""

import uuid
from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agente import instrucciones
from app.agente.cliente import ResultadoAgente
from app.dependencies import get_current_user
from app.main import app
from app.models.agente import AgenteCorrida
from app.models.catalogo import Cultivo, Suelo
from app.models.material_precio import MaterialPrecio
from app.models.proyecto import Proyecto
from app.models.usuario import Usuario
from app.schemas.agente import (
    CultivoRecomendado,
    EmisorRecomendado,
    EntradaAgente,
    MaterialAgente,
    PropuestaAgente,
    SistemaRecomendado,
)
from app.services import agente as agente_service
from app.services import precio as precio_service
from tests.conftest import create_user

RUBRO = "Tubería principal"
DESCRIPCION = "PVC 32 mm"
UNIDAD = "m"
FUENTE = "https://precios.example/tuberia"


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="precios4@example.com")


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


def _material(**extra) -> dict:
    base = {
        "rubro": RUBRO,
        "descripcion": DESCRIPCION,
        "cantidad": 10.0,
        "unidad": UNIDAD,
        "moneda": "BOB",
        "precio_unitario_bs": 8.0,
        "fuente_url": FUENTE,
    }
    base.update(extra)
    return base


def _propuesta(materiales: list[dict]) -> PropuestaAgente:
    return PropuestaAgente(
        cultivos=[
            CultivoRecomendado(
                cultivo_codigo="papa",
                nombre="Papa",
                color="#8D6E63",
                area_m2=200.0,
                demanda_l_m2_dia=2.0,
                ciclo_dias=120,
                justificacion="Es el cultivo que pidió el usuario.",
            )
        ],
        sistema=SistemaRecomendado(
            tipo="goteo",
            emisor=EmisorRecomendado(tipo="gotero", caudal_lh=2.0, separacion_m=0.3),
            separacion_laterales_m=0.5,
            bomba_hp=1.0,
            num_sectores=1,
        ),
        materiales=[MaterialAgente(**material) for material in materiales],
    )


def _proyecto(cliente: TestClient) -> str:
    proyecto = cliente.post("/proyectos", json={"nombre": "P", "zona": "Cuyo"})
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


def _disparar(
    cliente: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    proyecto_id: str,
    materiales: list[dict],
    *,
    restricciones: dict | None = None,
) -> dict:
    """Dispara la corrida con el agente reemplazado y devuelve su detalle."""

    propuesta = _propuesta(materiales)

    def agente_falso(_contexto, on_fase=None):
        return ResultadoAgente(
            propuesta=propuesta.model_copy(deep=True),
            fuentes=[],
            modelo="doble-de-test",
            modo="catalogo",
        )

    monkeypatch.setattr(agente_service, "ejecutar_agente", agente_falso)

    cuerpo = {"restricciones": restricciones} if restricciones is not None else None
    inicio = cliente.post(f"/proyectos/{proyecto_id}/agente", json=cuerpo)
    assert inicio.status_code == 202, inicio.text

    detalle = cliente.get(
        f"/proyectos/{proyecto_id}/agente/corridas/{inicio.json()['corrida_id']}"
    )
    assert detalle.status_code == 200, detalle.text
    return detalle.json()


def _correr(
    cliente: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    proyecto_id: str,
    materiales: list[dict],
    *,
    restricciones: dict | None = None,
) -> dict:
    """Dispara la corrida con el agente reemplazado y devuelve su salida congelada."""

    detalle = _disparar(
        cliente,
        monkeypatch,
        proyecto_id,
        materiales,
        restricciones=restricciones,
    )
    assert detalle["estado"] == "ok", detalle["error_detalle"]
    return detalle["salida"]


def _filas(db_session: Session) -> list[MaterialPrecio]:
    return list(db_session.scalars(select(MaterialPrecio)).all())


# --------------------------------------------------------------------------- #
# S6 — guardar lo encontrado y reutilizarlo en corridas de otros usuarios
# --------------------------------------------------------------------------- #


def test_el_precio_guardado_se_reutiliza_en_la_corrida_de_otro_usuario(
    cliente_autenticado: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    salida = _correr(cliente, monkeypatch, pid, [_material()])

    # El precio del agente queda guardado con su unidad, moneda, fuente y fecha.
    assert salida["materiales"][0]["total_bs"] == pytest.approx(80.0)
    filas = _filas(db_session)
    assert len(filas) == 1
    fila = filas[0]
    assert fila.rubro == RUBRO
    assert fila.descripcion == DESCRIPCION
    assert fila.unidad == UNIDAD
    assert fila.moneda == "BOB"
    assert float(fila.precio_unitario_bs) == pytest.approx(8.0)
    assert fila.fuente_url == FUENTE
    assert fila.recuperado_en is not None
    assert fila.actualizado_en is not None

    # Otro usuario, otro proyecto: el agente no trae precio y se reutiliza el de la
    # base, marcado como reutilizado y con la fecha del precio original.
    otro = create_user(db_session, email="otro-precios@example.com")
    app.dependency_overrides[get_current_user] = lambda: otro
    pid_otro = _proyecto(cliente)

    salida_otro = _correr(
        cliente,
        monkeypatch,
        pid_otro,
        [_material(precio_unitario_bs=None, fuente_url=None)],
    )

    material = salida_otro["materiales"][0]
    assert material["precio_unitario_bs"] == pytest.approx(8.0)
    assert material["total_bs"] == pytest.approx(80.0)
    assert material["reutilizado"] is True
    assert material["fuente_url"] == FUENTE
    assert material["recuperado_en"] is not None
    # Reutilizar no duplica la fila ni la toca como si fuera un precio nuevo.
    assert len(_filas(db_session)) == 1


def test_un_precio_vencido_se_vuelve_a_investigar(
    cliente_autenticado: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = cliente_autenticado
    db_session.add(
        MaterialPrecio(
            clave=precio_service.clave(RUBRO, DESCRIPCION, UNIDAD),
            rubro=RUBRO,
            descripcion=DESCRIPCION,
            unidad=UNIDAD,
            moneda="BOB",
            precio_unitario_bs=5.0,
            fuente_url="https://precios.example/viejo",
            recuperado_en=datetime.now(timezone.utc) - timedelta(days=120),
        )
    )
    db_session.commit()

    pid = _proyecto(cliente)
    salida = _correr(
        cliente, monkeypatch, pid, [_material(precio_unitario_bs=None, fuente_url=None)]
    )

    material = salida["materiales"][0]
    assert material["precio_unitario_bs"] is None
    assert material["total_bs"] is None
    assert material["reutilizado"] is False

    # El agente vuelve a investigar: el precio nuevo reemplaza al vencido, sin duplicar.
    pid_nuevo = _proyecto(cliente)
    salida_nueva = _correr(
        cliente,
        monkeypatch,
        pid_nuevo,
        [_material(precio_unitario_bs=9.5, fuente_url="https://precios.example/nuevo")],
    )
    assert salida_nueva["materiales"][0]["precio_unitario_bs"] == pytest.approx(9.5)

    filas = _filas(db_session)
    assert len(filas) == 1
    assert float(filas[0].precio_unitario_bs) == pytest.approx(9.5)
    assert filas[0].fuente_url == "https://precios.example/nuevo"
    assert precio_service.reutilizar(
        db_session, [MaterialAgente(**_material(precio_unitario_bs=None))], 90
    ) == 1


def test_la_correccion_conserva_la_moneda_del_precio(db_session: Session) -> None:
    """La moneda que informó el agente viaja hasta la base (S6).

    La corrección determinística reconstruye el material: si no copia ``moneda``, un
    precio en USD se guarda como BOB.
    """

    from app.agente.validacion import corregir

    corregida = corregir(
        _propuesta([_material(moneda="USD", precio_unitario_bs=1.2)]),
        catalogo={
            "papa": {
                "nombre": "Papa",
                "color": "#8D6E63",
                "demanda_agua_l_m2_dia": 2.0,
                "ciclo_dias": 120,
            }
        },
        area_m2=200.0,
        total_fuentes=0,
    )

    material = corregida.materiales[0]
    assert material.moneda == "USD"
    assert precio_service.guardar(db_session, [material]) == 1
    assert _filas(db_session)[0].moneda == "USD"


def test_guardar_actualiza_la_misma_fila_sin_duplicar(db_session: Session) -> None:
    primero = MaterialAgente(**_material())
    segundo = MaterialAgente(**_material(precio_unitario_bs=12.0))

    assert precio_service.guardar(db_session, [primero]) == 1
    assert precio_service.guardar(db_session, [segundo]) == 1

    filas = _filas(db_session)
    assert len(filas) == 1
    assert float(filas[0].precio_unitario_bs) == pytest.approx(12.0)


def test_no_se_guardan_precios_nulos_ni_no_positivos(db_session: Session) -> None:
    materiales = [
        MaterialAgente(**_material(precio_unitario_bs=None)),
        MaterialAgente(**_material(rubro="Tanque", precio_unitario_bs=0.0)),
        MaterialAgente(**_material(rubro="Bomba", precio_unitario_bs=-150.0)),
    ]

    assert precio_service.guardar(db_session, materiales) == 0
    assert _filas(db_session) == []


def test_el_total_se_completa_con_cantidad_y_precio(
    cliente_autenticado: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    salida = _correr(
        cliente,
        monkeypatch,
        pid,
        [
            _material(cantidad=10.0, precio_unitario_bs=8.0, total_bs=None),
            _material(
                rubro="Filtro de anillas",
                descripcion="Filtro 2 pulgadas",
                cantidad=2.0,
                unidad="u",
                precio_unitario_bs=None,
                total_bs=None,
            ),
            _material(
                rubro="Válvula de bola",
                descripcion="Válvula 1 pulgada",
                cantidad=3.0,
                unidad="u",
                precio_unitario_bs=45.0,
                total_bs=999.0,
            ),
        ],
    )

    por_rubro = {material["rubro"]: material for material in salida["materiales"]}
    assert por_rubro[RUBRO]["total_bs"] == pytest.approx(80.0)
    # Sin precio no hay total: nunca se inventa un cero.
    assert por_rubro["Filtro de anillas"]["total_bs"] is None
    # Un total que el agente ya informó se respeta.
    assert por_rubro["Válvula de bola"]["total_bs"] == pytest.approx(999.0)


# --------------------------------------------------------------------------- #
# S6 — el cómputo contra el presupuesto del paso 3
# --------------------------------------------------------------------------- #


def test_el_bom_que_supera_el_presupuesto_lo_advierte(
    cliente_autenticado: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    # 100 m × 15 Bs = 1500 Bs contra un presupuesto de 1000 Bs.
    salida = _correr(
        cliente,
        monkeypatch,
        pid,
        [_material(cantidad=100.0, precio_unitario_bs=15.0)],
        restricciones={"presupuesto_bs": 1000.0},
    )

    alertas = [
        alerta
        for alerta in salida["advertencias"]
        if alerta["codigo"] == "PRESUPUESTO_EXCEDIDO"
    ]
    assert len(alertas) == 1
    assert "1500.00" in alertas[0]["mensaje"]
    assert "1000.00" in alertas[0]["mensaje"]
    assert salida["materiales"][0]["precio_unitario_bs"] == pytest.approx(15.0)

    # Dentro del presupuesto no hay advertencia inventada.
    pid_dentro = _proyecto(cliente)
    dentro = _correr(
        cliente,
        monkeypatch,
        pid_dentro,
        [_material(cantidad=10.0, precio_unitario_bs=15.0)],
        restricciones={"presupuesto_bs": 1000.0},
    )
    assert all(
        alerta["codigo"] != "PRESUPUESTO_EXCEDIDO"
        for alerta in dentro["advertencias"]
    )


# --------------------------------------------------------------------------- #
# S6 — contexto del agente con los precios vigentes
# --------------------------------------------------------------------------- #


def test_el_contexto_del_agente_lleva_solo_los_precios_vigentes(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    proyecto = db_session.get(Proyecto, uuid.UUID(pid))
    assert proyecto is not None

    precio_service.guardar(db_session, [MaterialAgente(**_material())])
    db_session.add(
        MaterialPrecio(
            clave=precio_service.clave("Tanque", "Tanque 1000 L", "u"),
            rubro="Tanque",
            descripcion="Tanque 1000 L",
            unidad="u",
            moneda="BOB",
            precio_unitario_bs=900.0,
            recuperado_en=datetime.now(timezone.utc) - timedelta(days=200),
        )
    )
    db_session.commit()

    inicio = agente_service.iniciar_corrida(db_session, proyecto)
    corrida = db_session.get(AgenteCorrida, inicio.corrida_id)
    assert corrida is not None
    entrada = EntradaAgente.model_validate(corrida.entrada)
    contexto = agente_service._contexto_desde_corrida(db_session, proyecto, entrada)

    assert [precio["rubro"] for precio in contexto.precios] == [RUBRO]
    assert contexto.precios[0]["precio_unitario_bs"] == pytest.approx(8.0)

    mensaje = instrucciones.construir_mensaje(
        contexto.entrada,
        catalogo=contexto.catalogo,
        suelo=contexto.suelo,
        riego_actual=contexto.riego_actual,
        bloques=contexto.bloques,
        precios=contexto.precios,
    )
    assert "precios_conocidos" in mensaje
    assert RUBRO in mensaje
    assert FUENTE in mensaje
    assert "no lo vuelvas a investigar" in mensaje
    # El vencido no se ofrece: hay que investigarlo de nuevo.
    assert "Tanque 1000 L" not in mensaje


# --------------------------------------------------------------------------- #
# B1 — el guardado no puede romper la corrida ni duplicar claves
# --------------------------------------------------------------------------- #


def test_dos_rubros_que_solo_difieren_en_espacios_internos_no_rompen_la_corrida(
    cliente_autenticado: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dos materiales del mismo lote con la misma clave: una fila, corrida en ok."""

    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    salida = _correr(
        cliente,
        monkeypatch,
        pid,
        [
            _material(descripcion="PVC 32 mm"),
            _material(descripcion="PVC  32  mm", precio_unitario_bs=9.5),
        ],
    )

    # La propuesta congelada conserva los dos rubros del agente.
    assert [material["descripcion"] for material in salida["materiales"]] == [
        "PVC 32 mm",
        "PVC  32  mm",
    ]

    filas = _filas(db_session)
    assert len(filas) == 1
    assert filas[0].descripcion in ("PVC 32 mm", "PVC  32  mm")
    assert float(filas[0].precio_unitario_bs) == pytest.approx(9.5)


def test_una_corrida_no_queda_en_corriendo_si_falla_el_guardado_de_precios(
    cliente_autenticado: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)

    def boom(_db, _materiales):
        raise RuntimeError("la base rechazó el guardado")

    monkeypatch.setattr(
        "app.services.agente.precio_service.guardar", boom
    )

    detalle = _disparar(cliente, monkeypatch, pid, [_material()])

    assert detalle["estado"] == "error"
    assert "la base rechazó el guardado" in (detalle["error_detalle"] or "")
    assert detalle["salida"] is None
    assert detalle["terminado_en"] is not None


def test_unidades_equivalentes_colapsan_en_una_sola_fila(db_session: Session) -> None:
    tuberia = [
        MaterialAgente(**_material(unidad=unidad))
        for unidad in ("m", "mt", "ML", "Metro", "metros", "metro lineal")
    ]
    valvulas = [
        MaterialAgente(
            **_material(
                rubro="Válvula de bola",
                descripcion="Válvula 1 pulgada",
                unidad=unidad,
            )
        )
        for unidad in ("u", "un", "und", "unidad", "pza", "pieza")
    ]

    for material in tuberia + valvulas:
        assert precio_service.guardar(db_session, [material]) == 1

    filas = _filas(db_session)
    assert len(filas) == 2
    assert sorted(fila.unidad for fila in filas) == ["m", "u"]


# --------------------------------------------------------------------------- #
# A3 — el prompt no se contamina con precios de otras familias
# --------------------------------------------------------------------------- #


def test_el_prompt_no_lleva_precios_de_familias_ajenas(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)
    proyecto = db_session.get(Proyecto, uuid.UUID(pid))
    assert proyecto is not None

    precio_service.guardar(
        db_session,
        [
            MaterialAgente(**_material()),
            MaterialAgente(
                **_material(rubro="Filtro de anillas", descripcion="Filtro 2\"", unidad="u")
            ),
            MaterialAgente(
                **_material(rubro="Malla antigranizo", descripcion="Malla 80%", unidad="m")
            ),
            MaterialAgente(
                **_material(rubro="Semilla de maíz", descripcion="Bolsa 20 kg", unidad="u")
            ),
        ],
    )

    inicio = agente_service.iniciar_corrida(db_session, proyecto)
    corrida = db_session.get(AgenteCorrida, inicio.corrida_id)
    assert corrida is not None
    entrada = EntradaAgente.model_validate(corrida.entrada)
    contexto = agente_service._contexto_desde_corrida(db_session, proyecto, entrada)

    rubros = {precio["rubro"] for precio in contexto.precios}
    assert rubros == {RUBRO, "Filtro de anillas"}
    assert not any("Malla" in rubro or "Semilla" in rubro for rubro in rubros)
    # Tope del contexto: 40 precios, no 200.
    assert precio_service.MAX_PRECIOS_CONTEXTO == 40
