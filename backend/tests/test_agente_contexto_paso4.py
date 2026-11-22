"""Contrato del agente para el informe del paso 4 (T1).

Cubre S5 (la entrada lleva las fichas del cultivo, del suelo, del terreno y las
restricciones del paso 3), S4 (imágenes con atribución por cultivo y equipo de
cabecera) y S6 en su parte de contrato (materiales con precio y fuente). No ejecuta
el modelo: todo lo que se prueba es determinístico.
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agente.instrucciones import construir_mensaje
from app.agente.validacion import corregir
from app.dependencies import get_current_user
from app.main import app
from app.models.agente import AgenteCorrida
from app.models.catalogo import Cultivo, Suelo
from app.models.proyecto import Proyecto
from app.models.usuario import Usuario
from app.schemas.agente import (
    CifrasAgente,
    CorridaIniciarIn,
    CultivoRecomendado,
    EmisorRecomendado,
    EntradaAgente,
    MaterialAgente,
    ProductoDeseado,
    PropuestaAgente,
    RecomendacionFinal,
    RestriccionesEntrada,
    SistemaRecomendado,
    TurnoSectorAgente,
)
from app.services import agente as agente_service
from tests.conftest import create_user

AREA_TERRENO = 200


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="paso4@example.com")


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
            # Papa: la fila del catálogo ya tiene toda la ficha del paso 2.
            Cultivo(
                codigo="papa",
                nombre="Papa",
                icono="P",
                color="#8D6E63",
                demanda_agua_l_m2_dia=2.0,
                ciclo_dias=120,
                kc=1.15,
                profundidad_raiz_cm=40,
                densidad_plantas_m2=4.0,
                meses_siembra=[3, 4, 9, 10],
                aptitud_suelo={
                    "franco": {
                        "veredicto": "apto",
                        "motivo": "Suelo equilibrado.",
                        "fuente": "Ficha curada AgroPlan",
                    }
                },
                fuentes=[
                    {
                        "tipo": "manual",
                        "titulo": "Ficha técnica curada AgroPlan",
                        "url": None,
                        "fragmento": "Demanda y ciclo del catálogo base",
                    }
                ],
                activo=True,
            ),
            # Lechuga: fila vieja sin la ficha nueva; la completa la ficha curada.
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
                retencion_agua_mm_m=180.0,
            ),
        ]
    )
    db_session.commit()


def _proyecto_con_cultivos(cliente: TestClient) -> str:
    proyecto = cliente.post("/proyectos", json={"nombre": "Finca Paso 4", "zona": "Cuyo"})
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
            "profundidad_nivel_dinamico_m": 35,
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


# --------------------------------------------------------------------------- #
# S5 — la entrada lleva todo lo modelado
# --------------------------------------------------------------------------- #


def test_entrada_lleva_fichas_suelo_terreno_y_restricciones(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    proyecto_id = _proyecto_con_cultivos(cliente)
    proyecto = db_session.get(Proyecto, uuid.UUID(proyecto_id))
    assert proyecto is not None

    restricciones = RestriccionesEntrada(
        energia="solar", tanque_l=5000, presupuesto_bs=12000
    )
    inicio = agente_service.iniciar_corrida(
        db_session, proyecto, restricciones=restricciones
    )

    corrida = db_session.get(AgenteCorrida, inicio.corrida_id)
    assert corrida is not None
    entrada = EntradaAgente.model_validate(corrida.entrada)

    # Ficha por producto: el catálogo manda y la ficha curada completa lo que falta.
    por_codigo = {producto.cultivo_codigo: producto for producto in entrada.productos}
    papa = por_codigo["papa"]
    assert papa.kc == 1.15
    assert papa.profundidad_raiz_cm == 40
    assert papa.densidad_plantas_m2 == 4.0
    assert papa.meses_siembra == [3, 4, 9, 10]
    assert papa.aptitud_suelo["franco"].veredicto == "apto"
    assert papa.fuentes and papa.fuentes[0].tipo == "manual"

    lechuga = por_codigo["lechuga"]
    assert lechuga.kc is not None  # viene de app/agente/fichas/lechuga.json
    assert lechuga.profundidad_raiz_cm is not None
    assert lechuga.meses_siembra
    assert lechuga.fuentes

    # Ficha del suelo.
    assert entrada.infiltracion_mm_h == 12.0
    assert entrada.retencion_agua_mm_m == 180.0

    # Terreno derivado por el backend, nunca enviado por el cliente.
    assert entrada.perimetro_m == 60.0
    assert entrada.profundidad_nivel_dinamico_m == 35.0
    assert entrada.geometria is not None and len(entrada.geometria.vertices) == 4
    assert entrada.lados_m is not None and [l.longitud_m for l in entrada.lados_m] == [
        10.0,
        20.0,
        10.0,
        20.0,
    ]

    # Restricciones del paso 3 congeladas con la corrida.
    assert entrada.restricciones is not None
    assert entrada.restricciones.energia == "solar"
    assert entrada.restricciones.tanque_l == 5000
    assert entrada.restricciones.presupuesto_bs == 12000


def test_mensaje_del_agente_usa_las_fichas_y_las_restricciones() -> None:
    entrada = EntradaAgente(
        proyecto_id=uuid.uuid4(),
        productos=[
            ProductoDeseado(
                nombre="Papa",
                cultivo_codigo="papa",
                prioridad=1,
                kc=1.15,
                aptitud_suelo={"franco": {"veredicto": "apto", "motivo": "ok"}},
                profundidad_raiz_cm=40,
                densidad_plantas_m2=4.0,
                meses_siembra=[3, 4],
            )
        ],
        area_m2=AREA_TERRENO,
        suelo_codigo="franco",
        fuente_agua="pozo",
        caudal_efectivo_m3h=3.0,
        caudal_origen="asumido",
        infiltracion_mm_h=12.0,
        retencion_agua_mm_m=180.0,
        perimetro_m=60.0,
        profundidad_nivel_dinamico_m=35.0,
        restricciones=RestriccionesEntrada(energia="solar", presupuesto_bs=12000),
    )

    mensaje = construir_mensaje(
        entrada,
        catalogo=[{"codigo": "papa", "kc": 1.15, "meses_siembra": [3, 4]}],
        suelo={"codigo": "franco", "retencion_agua_mm_m": 180.0},
        riego_actual=None,
        bloques=1,
    )

    for clave in (
        '"kc"',
        '"aptitud_suelo"',
        '"profundidad_raiz_cm"',
        '"densidad_plantas_m2"',
        '"meses_siembra"',
        '"retencion_agua_mm_m"',
        '"lados_m"',
        '"geometria"',
        '"restricciones"',
        '"solar"',
        "cifras",
        "materiales",
        "recomendaciones",
        "imagen_url",
    ):
        assert clave in mensaje, f"falta {clave} en el mensaje del agente"


# --------------------------------------------------------------------------- #
# Contrato de salida y saneo
# --------------------------------------------------------------------------- #


def _propuesta_minima() -> PropuestaAgente:
    return PropuestaAgente(
        cultivos=[
            CultivoRecomendado(
                cultivo_codigo="papa",
                nombre="Papa",
                area_m2=AREA_TERRENO,
                demanda_l_m2_dia=2.0,
                justificacion="prueba",
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


def test_propuesta_tiene_defaults_seguros() -> None:
    propuesta = _propuesta_minima()

    assert propuesta.cifras == CifrasAgente()
    assert propuesta.cifras.presion_trabajo_bar is None
    assert propuesta.cifras.turnos == []
    assert propuesta.materiales == []
    assert propuesta.recomendaciones == []
    assert propuesta.cultivos[0].imagen_url is None
    assert propuesta.sistema.imagen_url is None


def test_corrida_iniciar_in_acepta_restricciones_y_rechaza_energia_invalida() -> None:
    cuerpo = CorridaIniciarIn.model_validate(
        {
            "siembra": "2026-11-20",
            "restricciones": {
                "energia": "red-electrica",
                "tanque_l": 5000,
                "presupuesto_bs": 8000,
            },
        }
    )
    assert cuerpo.restricciones is not None
    assert cuerpo.restricciones.energia == "red-electrica"

    with pytest.raises(ValidationError):
        CorridaIniciarIn.model_validate({"restricciones": {"energia": "nuclear"}})


def _propuesta_cruda_con_extras() -> PropuestaAgente:
    return PropuestaAgente(
        cultivos=[
            CultivoRecomendado(
                cultivo_codigo="papa",
                nombre="Papa",
                area_m2=AREA_TERRENO,
                demanda_l_m2_dia=2.0,
                justificacion="prueba",
                imagen_url="javascript:alert(1)",
                imagen_fuente_url="https://fichas.example/papa.jpg",
            )
        ],
        sistema=SistemaRecomendado(
            tipo="goteo",
            emisor=EmisorRecomendado(tipo="gotero", caudal_lh=2, separacion_m=0.3),
            separacion_laterales_m=0.5,
            bomba_hp=1,
            num_sectores=2,
            imagen_url="ftp://equipos.example/cabezal.jpg",
            imagen_fuente_url="https://equipos.example/cabezal",
        ),
        cifras=CifrasAgente(
            presion_trabajo_bar=-1,
            eficiencia_pct=130,
            demanda_pico_l_dia=0,
            autonomia_dias=-2,
            tiempo_riego_h=30,
            turnos=[
                TurnoSectorAgente(sector=1, horas=3, caudal_lh=900),
                TurnoSectorAgente(sector=1, horas=5, caudal_lh=900),
                TurnoSectorAgente(sector=9, horas=2, caudal_lh=900),
                TurnoSectorAgente(sector=2, horas=-1, caudal_lh=-5),
            ],
        ),
        materiales=[
            MaterialAgente(
                rubro="Riego",
                descripcion="Tubería PVC Ø32 mm",
                cantidad=78,
                unidad="m",
                precio_unitario_bs=-5,
                total_bs=-390,
                fuente_url="data:text/plain,precio",
            ),
            # Duplicado exacto del anterior: se descarta.
            MaterialAgente(
                rubro="Riego",
                descripcion="Tubería PVC Ø32 mm",
                cantidad=78,
                unidad="m",
                precio_unitario_bs=10,
                total_bs=780,
                fuente_url="https://ferreteria.example/pvc32",
            ),
            MaterialAgente(
                rubro="Riego",
                descripcion="Gotero 2 L/h",
                cantidad=0,
                unidad="u",
                precio_unitario_bs=1,
                total_bs=0,
            ),
            MaterialAgente(
                rubro="Cabezal",
                descripcion="Bomba 1 HP",
                cantidad=1,
                unidad="u",
                precio_unitario_bs=1200,
                total_bs=1200,
                fuente_url="https://equipos.example/bomba",
            ),
        ],
        recomendaciones=[
            RecomendacionFinal(titulo="  ", detalle="sin título", justificacion=""),
            RecomendacionFinal(
                titulo="Operar por turnos",
                detalle="S1 y S2 secuenciales.",
                justificacion="No superar el aforo.",
            ),
            RecomendacionFinal(
                titulo="Operar por turnos",
                detalle="Repetida.",
                justificacion="Duplicada.",
            ),
        ],
    )


def test_validacion_sanea_urls_rangos_y_duplicados() -> None:
    corregida = corregir(
        _propuesta_cruda_con_extras(),
        catalogo={
            "papa": {
                "nombre": "Papa",
                "color": "#8D6E63",
                "demanda_agua_l_m2_dia": 2.0,
                "ciclo_dias": 120,
            }
        },
        area_m2=AREA_TERRENO,
        total_fuentes=1,
    )

    cultivo = corregida.cultivos[0]
    assert cultivo.imagen_url is None
    assert cultivo.imagen_fuente_url == "https://fichas.example/papa.jpg"
    assert corregida.sistema.imagen_url is None
    assert corregida.sistema.imagen_fuente_url == "https://equipos.example/cabezal"

    cifras = corregida.cifras
    assert cifras.presion_trabajo_bar is None
    assert cifras.eficiencia_pct == 100.0
    assert cifras.demanda_pico_l_dia is None
    assert cifras.autonomia_dias is None
    assert cifras.tiempo_riego_h == 24.0
    assert [turno.sector for turno in cifras.turnos] == [1, 2]
    assert cifras.turnos[0].horas == 3.0
    assert cifras.turnos[1].horas is None
    assert cifras.turnos[1].caudal_lh is None

    assert len(corregida.materiales) == 2
    pvc = corregida.materiales[0]
    assert pvc.precio_unitario_bs is None
    assert pvc.total_bs is None
    assert pvc.fuente_url is None
    bomba = corregida.materiales[1]
    assert bomba.precio_unitario_bs == 1200
    assert bomba.fuente_url == "https://equipos.example/bomba"

    assert len(corregida.recomendaciones) == 1
    assert corregida.recomendaciones[0].titulo == "Operar por turnos"
