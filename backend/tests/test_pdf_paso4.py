"""Informe PDF del paso 4 (S8): endpoint descargable y armador del documento.

Cubre la regla de S8: ``POST /proyectos/{id}/pdf`` devuelve un PDF real, el proyecto
sin red responde 4xx en vez de un PDF vacío y el armador del informe arma las
secciones con las cifras del resultado, sin salir a la red.
"""

from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.main import app
from app.models.catalogo import Cultivo, Suelo
from app.models.usuario import Usuario
from app.schemas.agente import ResultadoProyectoOut
from app.schemas.comun import Advertencia
from app.schemas.proyecto import TerrenoOut
from app.services.informe_pdf import construir_informe, generar_pdf
from tests.conftest import create_user
from tests.test_resultado_paso4 import (
    _aplicar,
    _corrida,
    _proyecto,
    _salida,
)


@pytest.fixture()
def usuario(db_session: Session) -> Usuario:
    return create_user(db_session, email="pdf4@example.com")


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


SALIDA = {
    "cifras": {
        "presion_trabajo_bar": 4.5,
        "eficiencia_pct": 85.0,
        "demanda_pico_l_dia": 100.0,
        "autonomia_dias": 3.0,
        "tiempo_riego_h": 1.0,
    },
    "materiales": [
        {
            "rubro": "Tubería principal",
            "descripcion": "PVC 32 mm",
            "cantidad": 10.0,
            "unidad": "m",
            "precio_unitario_bs": 150.0,
            "total_bs": 1500.0,
            "fuente_url": "https://precios.example/tuberia",
        }
    ],
    "recomendaciones": [
        {
            "titulo": "Revisar el filtro",
            "detalle": "Limpiar el filtro cada semana.",
            "justificacion": "El agua del pozo trae sedimentos.",
        }
    ],
}

ADVERTENCIA = {
    "codigo": "PRESUPUESTO_EXCEDIDO",
    "mensaje": "El cómputo supera el presupuesto del paso 3.",
}


def _proyecto_con_informe(cliente: TestClient, db_session: Session) -> tuple[str, dict]:
    pid = _proyecto(cliente)
    salida = _salida(**SALIDA)
    salida["advertencias"] = [ADVERTENCIA]
    corrida = _corrida(
        pid,
        db_session,
        salida,
        con_fuentes=True,
        con_recomendaciones=True,
        restricciones={"presupuesto_bs": 500},
    )
    return pid, _aplicar(cliente, pid, corrida.id)


def test_el_endpoint_devuelve_un_pdf_descargable(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid, _ = _proyecto_con_informe(cliente, db_session)

    respuesta = cliente.post(f"/proyectos/{pid}/pdf")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"].startswith("application/pdf")
    assert respuesta.headers["content-disposition"].startswith("attachment;")
    assert 'filename="informe-p.pdf"' in respuesta.headers["content-disposition"]
    assert respuesta.content.startswith(b"%PDF")
    assert len(respuesta.content) > 1000


def test_sin_diseno_generado_responde_4xx_y_no_un_pdf_vacio(
    cliente_autenticado: TestClient,
) -> None:
    cliente = cliente_autenticado
    pid = _proyecto(cliente)

    respuesta = cliente.post(f"/proyectos/{pid}/pdf")

    assert 400 <= respuesta.status_code < 500
    assert "application/pdf" not in respuesta.headers.get("content-type", "")
    assert respuesta.json()["detail"]
    assert not respuesta.content.startswith(b"%PDF")


def test_el_armador_incluye_las_secciones_y_las_cifras_del_resultado(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    cliente = cliente_autenticado
    pid, cuerpo = _proyecto_con_informe(cliente, db_session)
    resultado = ResultadoProyectoOut.model_validate(cuerpo)
    terreno = TerrenoOut.model_validate(
        cliente.get(f"/proyectos/{pid}/terreno").json()
    )

    documento = construir_informe(
        resultado, terreno, fecha=date(2026, 11, 21)
    )

    titulos = [seccion.titulo for seccion in documento.secciones]
    assert titulos == [
        "Datos del terreno",
        "Zonificación",
        "Tecnología y cabezal",
        "Balance hidráulico",
        "Cómputo de materiales",
        "Calendario",
        "Recomendaciones",
        "Fuentes consultadas",
        "Advertencias",
    ]
    assert documento.titulo == "P"
    assert documento.marca_agua == "Estimación preliminar"

    texto = "\n".join(
        linea for seccion in documento.secciones for linea in seccion.lineas
    )
    # Terreno real del paso 1.
    assert "Lote 1" in texto
    assert "200" in texto  # área real del terreno de la prueba
    # Zonificación y fechas del cultivo.
    assert "Papa" in texto
    assert "siembra" in texto.lower()
    assert "cosecha" in texto.lower()
    # Balance hidráulico del motor y el ajuste del agente (S3).
    assert "1.5" in texto  # presión que calculó el motor
    assert "4.5" in texto  # presión que propuso el agente
    assert "de 4.5 a 1.5" in texto
    assert "El motor recalculó la presión de trabajo" in texto
    # Cómputo con precio y total contra el presupuesto.
    assert "PVC 32 mm" in texto
    assert "1500" in texto
    assert "500" in texto
    # Recomendaciones con su justificación, fuentes y advertencias.
    assert "Revisar el filtro" in texto
    assert "El agua del pozo trae sedimentos." in texto
    assert "https://precios.example/tuberia" in texto
    assert "supera el presupuesto del paso 3" in texto
    assert "el cómputo supera el presupuesto" in texto


def test_la_marca_de_agua_aparece_en_cada_pagina(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    """Un informe largo obliga a varias páginas y todas llevan la marca (S8)."""

    cliente = cliente_autenticado
    pid, cuerpo = _proyecto_con_informe(cliente, db_session)
    resultado = ResultadoProyectoOut.model_validate(cuerpo)
    terreno = TerrenoOut.model_validate(
        cliente.get(f"/proyectos/{pid}/terreno").json()
    )
    resultado.advertencias.extend(
        [
            Advertencia(
                codigo=f"AVISO_{indice}",
                mensaje=f"Advertencia de prueba {indice} " + "x" * 80,
                bloqueante=False,
                campo=None,
            )
            for indice in range(40)
        ]
    )

    pdf = generar_pdf(construir_informe(resultado, terreno))

    # ReportLab escribe la «ó» como escape octal en el stream sin comprimir.
    marca = b"Estimaci\\363n preliminar"
    assert pdf.count(marca) >= 2


@pytest.mark.parametrize("clave", ["banana", "plano"])
def test_una_clave_no_soportada_no_devuelve_un_pdf_casi_vacio(
    cliente_autenticado: TestClient, db_session: Session, clave: str
) -> None:
    """S8: una sección pedida que no se imprime se rechaza, no se ignora en silencio."""
    cliente = cliente_autenticado
    pid, _ = _proyecto_con_informe(cliente, db_session)

    respuesta = cliente.post(f"/proyectos/{pid}/pdf", json={"incluir": [clave]})

    assert respuesta.status_code == 422, respuesta.text
    assert "incluir" in respuesta.text or clave in respuesta.text
    assert not respuesta.content.startswith(b"%PDF")


def test_incluir_vacio_devuelve_el_informe_completo(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    """S8: una lista vacía no puede producir un documento sin secciones."""
    cliente = cliente_autenticado
    pid, _ = _proyecto_con_informe(cliente, db_session)

    completo = cliente.post(f"/proyectos/{pid}/pdf")
    vacio = cliente.post(f"/proyectos/{pid}/pdf", json={"incluir": []})

    assert completo.status_code == 200, completo.text
    assert vacio.status_code == 200, vacio.text
    assert vacio.content.startswith(b"%PDF")
    assert abs(len(vacio.content) - len(completo.content)) < 100


def test_la_marca_de_agua_aparece_en_todas_las_paginas(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    """S8: la marca va en cada página, no sólo en la primera."""
    cliente = cliente_autenticado
    pid, cuerpo = _proyecto_con_informe(cliente, db_session)
    resultado = ResultadoProyectoOut.model_validate(cuerpo)
    resultado.advertencias.extend(
        Advertencia(codigo=f"AVISO_{indice}", mensaje=f"Advertencia {indice} " + "x" * 80)
        for indice in range(40)
    )
    terreno = TerrenoOut.model_validate(cliente.get(f"/proyectos/{pid}/terreno").json())

    pdf = generar_pdf(construir_informe(resultado, terreno))

    paginas = pdf.count(b"/Type /Page\n")
    assert paginas >= 3
    assert pdf.count(b"Estimaci\\363n preliminar") >= paginas


def test_un_dato_ausente_se_imprime_no_informado_y_nunca_cero(
    cliente_autenticado: TestClient, db_session: Session
) -> None:
    """S8/S10: un dato que no existe se imprime "no informado", nunca 0."""
    cliente = cliente_autenticado
    pid, cuerpo = _proyecto_con_informe(cliente, db_session)
    resultado = ResultadoProyectoOut.model_validate(cuerpo)
    resultado.diseno.cifras.autonomia_dias = None
    resultado.diseno.cifras.presion_trabajo_bar = None
    resultado.diseno.costo_total_bs = None
    resultado.diseno.presupuesto_bs = None
    resultado.diseno.presupuesto_excedido = None
    terreno = TerrenoOut.model_validate(cliente.get(f"/proyectos/{pid}/terreno").json())

    secciones = {
        seccion.titulo: seccion.lineas
        for seccion in construir_informe(resultado, terreno).secciones
    }

    assert "Autonomía del tanque: no informado" in secciones["Balance hidráulico"]
    assert "Presión de trabajo: no informado" in secciones["Balance hidráulico"]
    assert "Total del cómputo: no informado" in secciones["Cómputo de materiales"]
