"""Investigación de productos fuera del catálogo: ficha curada primero, web de respaldo.

Todos los casos corren con ``busqueda_web`` inyectado (fakes): no hay red ni ``agno``, y
el adaptador real sólo se toca para probar que falla cerrado cuando no hay credenciales.
"""

from __future__ import annotations

import json
import logging
import re

import pytest

from app.agente import fichas
from app.agente.fichas import FichaCultivo, buscar, listar, normalizar
from app.agente.investigacion import (
    COLOR_POR_DEFECTO,
    FRAGMENTO_MAX,
    InvestigacionError,
    ProductoNoReconocido,
    _contenido,
    investigar,
)
from app.core.config import settings

PATRON_CODIGO = re.compile(r"^[a-z0-9_]{2,30}$")
CATALOGO_VACIO: list[dict] = []


@pytest.fixture(autouse=True)
def _cache_de_fichas_limpia() -> None:
    """La cache de fichas es global: se limpia antes y después de cada test."""

    fichas._cargar.cache_clear()
    yield
    fichas._cargar.cache_clear()


# --------------------------------------------------------------------------- #
# Fichas curadas
# --------------------------------------------------------------------------- #


def test_listar_fichas_curadas_deterministico() -> None:
    cargadas = listar()

    codigos = [ficha.codigo for ficha in cargadas]
    assert codigos == sorted(codigos)
    assert {"papa", "lechuga", "maiz", "tomate", "quinoa", "zapallo"} <= set(codigos)
    assert all(isinstance(ficha, FichaCultivo) for ficha in cargadas)
    for ficha in cargadas:
        assert 0 < ficha.demanda_agua_l_m2_dia <= 20
        assert 1 <= ficha.ciclo_dias <= 730
        assert ficha.color.startswith("#") and len(ficha.color) == 7
        assert ficha.fuentes and ficha.fuentes[0].tipo == "manual"
    # Se leen una sola vez: dos llamadas devuelven el mismo contenido.
    assert [f.codigo for f in listar()] == codigos


def test_buscar_por_codigo_y_por_nombre_normalizado() -> None:
    assert normalizar("  MaÍz ") == "maiz"
    assert buscar("PAPA") is not None
    assert buscar("papa").codigo == "papa"  # type: ignore[union-attr]
    assert buscar("Maíz").codigo == "maiz"  # type: ignore[union-attr]
    assert buscar("quínoa").codigo == "quinoa"  # type: ignore[union-attr]
    assert buscar("cultivo inexistente") is None
    assert buscar("") is None


def test_ficha_invalida_se_descarta_con_warning(tmp_path, monkeypatch, caplog) -> None:
    valida = {
        "codigo": "ruda",
        "nombre": "Ruda",
        "icono": "R",
        "color": "#33691E",
        "demanda_agua_l_m2_dia": 1.2,
        "ciclo_dias": 300,
        "meses_siembra": [5, 6],
        "notas": "Aromática.",
        "fuentes": [{"tipo": "manual", "titulo": "Curada", "url": None, "fragmento": "base"}],
    }
    invalida = {**valida, "codigo": "rota", "color": "verde", "demanda_agua_l_m2_dia": 99}
    (tmp_path / "ruda.json").write_text(json.dumps(valida), encoding="utf-8")
    (tmp_path / "rota.json").write_text(json.dumps(invalida), encoding="utf-8")
    (tmp_path / "basura.json").write_text("{ no es json", encoding="utf-8")

    monkeypatch.setattr(fichas, "DIRECTORIO_FICHAS", tmp_path)
    fichas._cargar.cache_clear()

    with caplog.at_level(logging.WARNING, logger="app.agente.fichas"):
        cargadas = listar()

    assert [ficha.codigo for ficha in cargadas] == ["ruda"]
    mensajes = " ".join(registro.getMessage() for registro in caplog.records)
    assert "rota.json" in mensajes
    assert "basura.json" in mensajes


# --------------------------------------------------------------------------- #
# Camino híbrido
# --------------------------------------------------------------------------- #


def test_ficha_curada_gana_sin_red() -> None:
    llamadas: list[str] = []

    def fake(consulta: str) -> list[dict]:
        llamadas.append(consulta)
        raise AssertionError("no se debe consultar la web si hay ficha curada")

    resultado = investigar(
        "Quínoa", catalogo=CATALOGO_VACIO, busqueda_web=fake, max_busquedas=3
    )

    assert resultado.origen == "ficha"
    assert resultado.busquedas == 0
    assert llamadas == []
    assert resultado.codigo == "quinoa"
    assert resultado.meses_siembra == [3, 4, 9, 10]
    assert [fuente.tipo for fuente in resultado.fuentes] == ["manual"]
    assert resultado.fuentes[0].url is None


def test_ficha_curada_de_chia_resuelve_sin_red() -> None:
    """La chía no está en el catálogo: la ficha curada la resuelve sin gastar búsquedas."""

    def fake(consulta: str) -> list[dict]:
        raise AssertionError("la ficha curada no debe consultar la web")

    resultado = investigar("Chía", catalogo=CATALOGO_VACIO, busqueda_web=fake)

    assert resultado.codigo == "chia"
    assert resultado.origen == "ficha"
    assert resultado.busquedas == 0
    assert 0 < resultado.demanda_agua_l_m2_dia <= 20
    assert 1 <= resultado.ciclo_dias <= 730


def test_json_envuelto_en_cerco_de_markdown_se_parsea() -> None:
    """El modelo devuelve el JSON entre ```json: descartarlo perdía la investigación."""

    class Respuesta:
        content = '```json\n{"nombre": "Chía", "demanda_agua_l_m2_dia": 2.0}\n```'

    assert _contenido(Respuesta()) == {
        "nombre": "Chía",
        "demanda_agua_l_m2_dia": 2.0,
    }


def test_web_valida_cita_url_y_recorta_fragmento() -> None:
    llamadas: list[str] = []

    def fake(consulta: str) -> list[dict]:
        llamadas.append(consulta)
        return [
            {
                "titulo": "Ficha de arándano",
                "url": "https://example.org/arandano",
                "fragmento": "x" * 900,
                "demanda_agua_l_m2_dia": 3.2,
                "ciclo_dias": 180,
                "meses_siembra": [4, 5],
            }
        ]

    resultado = investigar(
        "Arándano", catalogo=CATALOGO_VACIO, busqueda_web=fake, max_busquedas=6
    )

    assert resultado.origen == "web"
    assert resultado.busquedas == 1
    assert len(llamadas) == 1
    assert resultado.codigo == "arandano"
    assert resultado.demanda_agua_l_m2_dia == 3.2
    assert resultado.ciclo_dias == 180
    assert resultado.meses_siembra == [4, 5]
    assert resultado.fuentes[0].tipo == "web"
    assert resultado.fuentes[0].url == "https://example.org/arandano"
    assert resultado.fuentes[0].fragmento is not None
    assert len(resultado.fuentes[0].fragmento) == FRAGMENTO_MAX


def test_presupuesto_nunca_se_excede() -> None:
    llamadas: list[str] = []

    def fake(consulta: str) -> list[dict]:
        llamadas.append(consulta)
        return [{"url": "https://example.org/sin-datos", "fragmento": "no dice nada útil"}]

    with pytest.raises(ProductoNoReconocido):
        investigar("Mburucuyá", catalogo=CATALOGO_VACIO, busqueda_web=fake, max_busquedas=3)

    assert 1 <= len(llamadas) <= 3


def test_dominios_fuera_de_rango_se_recortan() -> None:
    def fake(consulta: str) -> list[dict]:
        return [
            {
                "url": "https://example.org/extremo",
                "demanda_agua_l_m2_dia": 999,
                "ciclo_dias": 2000,
                "color": "verde",
                "icono": "ZZ",
            }
        ]

    resultado = investigar("Yacón", catalogo=CATALOGO_VACIO, busqueda_web=fake, max_busquedas=2)

    assert resultado.demanda_agua_l_m2_dia == 20.0
    assert resultado.ciclo_dias == 730
    assert resultado.color == COLOR_POR_DEFECTO
    # El icono siempre sale del nombre: la web no dicta presentación.
    assert resultado.icono == "Y"


def test_demanda_absurda_y_ciclo_negativo_no_producen_ficha() -> None:
    def fake(consulta: str) -> list[dict]:
        return [
            {
                "url": "https://example.org/invalido",
                "demanda_agua_l_m2_dia": 999,
                "ciclo_dias": -5,
            }
        ]

    with pytest.raises(ProductoNoReconocido):
        investigar("Chirimoya", catalogo=CATALOGO_VACIO, busqueda_web=fake, max_busquedas=2)


def test_sin_demanda_ni_ciclo_es_producto_no_reconocido() -> None:
    def fake(consulta: str) -> list[dict]:
        return [{"url": "https://example.org/nada", "fragmento": "texto sin números útiles"}]

    with pytest.raises(ProductoNoReconocido):
        investigar("Camu camu", catalogo=CATALOGO_VACIO, busqueda_web=fake, max_busquedas=2)


def test_busqueda_que_falla_es_error_de_investigacion() -> None:
    def fake(consulta: str) -> list[dict]:
        raise RuntimeError("timeout del proveedor")

    with pytest.raises(InvestigacionError) as excinfo:
        investigar("Mango", catalogo=CATALOGO_VACIO, busqueda_web=fake, max_busquedas=6)

    assert "timeout del proveedor" in str(excinfo.value)


def test_nombre_con_acentos_produce_slug_valido_y_estable() -> None:
    def fake(consulta: str) -> list[dict]:
        return [
            {
                "url": "https://example.org/quinoa-real",
                "demanda_agua_l_m2_dia": 2.4,
                "ciclo_dias": 150,
            }
        ]

    primero = investigar(
        "Quínoa Real", catalogo=CATALOGO_VACIO, busqueda_web=fake, max_busquedas=1
    )
    segundo = investigar(
        "QUINOA REAL", catalogo=CATALOGO_VACIO, busqueda_web=fake, max_busquedas=1
    )

    assert primero.codigo == "quinoa_real"
    assert PATRON_CODIGO.match(primero.codigo)
    assert segundo.codigo == primero.codigo


def test_codigo_que_ya_esta_en_el_catalogo_no_duplica() -> None:
    catalogo = [
        {
            "codigo": "kale",
            "nombre": "Kale",
            "icono": "K",
            "color": "#3949AB",
            "demanda_agua_l_m2_dia": 3.0,
            "ciclo_dias": 150,
            "meses_siembra": [2, 3],
        }
    ]

    def fake(consulta: str) -> list[dict]:
        return [
            {
                "url": "https://example.org/kale",
                "demanda_agua_l_m2_dia": 9.9,
                "ciclo_dias": 12,
            }
        ]

    # Kale no tiene ficha curada: el camino es la web, y el código ya existente en el
    # catálogo manda sobre lo que devuelva la búsqueda.
    resultado = investigar("Kale", catalogo=catalogo, busqueda_web=fake, max_busquedas=2)

    assert resultado.codigo == "kale"
    assert resultado.nombre == "Kale"
    assert resultado.demanda_agua_l_m2_dia == 3.0
    assert resultado.ciclo_dias == 150
    assert resultado.color == "#3949AB"
    assert resultado.meses_siembra == [2, 3]
    assert resultado.busquedas == 1


def test_fuentes_duplicadas_por_url_se_deduplican() -> None:
    def fake(consulta: str) -> list[dict]:
        return [
            {
                "url": "https://example.org/fruta",
                "titulo": "Ficha A",
                "fragmento": "A",
                "demanda_agua_l_m2_dia": 2.0,
                "ciclo_dias": 100,
            },
            {
                "url": "https://example.org/fruta",
                "titulo": "Ficha A repetida",
                "fragmento": "B",
            },
            {
                "url": "https://example.org/fruta-2",
                "titulo": "Ficha B",
                "fragmento": "C",
            },
        ]

    resultado = investigar("Pitanga", catalogo=CATALOGO_VACIO, busqueda_web=fake, max_busquedas=1)

    assert [fuente.url for fuente in resultado.fuentes] == [
        "https://example.org/fruta",
        "https://example.org/fruta-2",
    ]


def test_sin_api_key_y_sin_fake_no_inventa(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AGENTE_API_KEY", "")

    with pytest.raises(ProductoNoReconocido) as excinfo:
        investigar("Mburucuyá", catalogo=CATALOGO_VACIO)

    assert "AGENTE_API_KEY" in str(excinfo.value)
