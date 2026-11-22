"""Modo del reparto: catálogo (gratis) contra modelo (LLM).

La investigación de un producto que no está en el catálogo no depende de este modo:
ocurre igual en los dos, porque sin ella el producto no se puede usar.
"""

import uuid

import pytest

from app.agente import ContextoAgente, cliente, ejecutar
from app.core.config import settings
from app.schemas.agente import EntradaAgente, ProductoDeseado

CATALOGO = [
    {
        "codigo": "papa",
        "nombre": "Papa",
        "color": "#8D6E63",
        "demanda_agua_l_m2_dia": 2.0,
        "ciclo_dias": 120,
    }
]


def _contexto() -> ContextoAgente:
    return ContextoAgente(
        entrada=EntradaAgente(
            proyecto_id=uuid.uuid4(),
            productos=[ProductoDeseado(nombre="Papa", prioridad=1)],
            area_m2=1000,
            suelo_codigo="franco",
            fuente_agua="pozo",
            caudal_efectivo_m3h=3.0,
            caudal_origen="asumido",
        ),
        catalogo=CATALOGO,
    )


@pytest.fixture()
def modo(monkeypatch: pytest.MonkeyPatch):
    def configurar(modo: str, key: str) -> None:
        monkeypatch.setattr(settings, "AGENTE_MODO", modo, raising=False)
        monkeypatch.setattr(settings, "AGENTE_API_KEY", key, raising=False)

    return configurar


def test_modo_catalogo_no_llama_al_modelo_aunque_haya_clave(
    modo, monkeypatch: pytest.MonkeyPatch
) -> None:
    modo("catalogo", "sk-prueba")
    llamado = False

    def no_deberia(_contexto, on_fase=None):
        nonlocal llamado
        llamado = True
        raise AssertionError("AGENTE_MODO=catalogo no debe llamar al modelo")

    monkeypatch.setattr(cliente, "_propuesta_llm", no_deberia)

    resultado = ejecutar(_contexto())

    assert llamado is False
    assert resultado.modo == "catalogo"
    assert resultado.modelo == "catalogo"
    assert any(
        alerta.codigo == "AGENTE_SIN_CREDENCIALES" and "AGENTE_MODO" in alerta.mensaje
        for alerta in resultado.propuesta.advertencias
    )


def test_modo_llm_sin_clave_cae_a_catalogo(modo) -> None:
    modo("llm", "")

    resultado = ejecutar(_contexto())

    assert resultado.modo == "catalogo"
    assert any(
        alerta.codigo == "AGENTE_SIN_CREDENCIALES" and "credenciales" in alerta.mensaje
        for alerta in resultado.propuesta.advertencias
    )


def test_modo_llm_con_clave_usa_el_modelo(modo, monkeypatch: pytest.MonkeyPatch) -> None:
    modo("llm", "sk-prueba")
    from app.schemas.agente import (
        CultivoRecomendado,
        EmisorRecomendado,
        PropuestaAgente,
        SistemaRecomendado,
    )

    cruda = PropuestaAgente(
        cultivos=[
            CultivoRecomendado(
                cultivo_codigo="papa",
                nombre="Papa",
                area_m2=1000,
                demanda_l_m2_dia=2.0,
                justificacion="prueba",
            )
        ],
        sistema=SistemaRecomendado(
            tipo="goteo",
            emisor=EmisorRecomendado(tipo="gotero", caudal_lh=2, separacion_m=0.3),
            separacion_laterales_m=1.0,
            bomba_hp=1,
            num_sectores=1,
        ),
    )
    monkeypatch.setattr(
        cliente, "_propuesta_llm", lambda _contexto, on_fase=None: (cruda, 10, 20)
    )

    resultado = ejecutar(_contexto())

    assert resultado.modo == "llm"
    assert resultado.tokens_entrada == 10
    assert resultado.tokens_salida == 20
    assert resultado.propuesta.cultivos[0].area_m2 == 1000
