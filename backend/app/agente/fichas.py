"""Fichas agronómicas curadas de AgroPlan, versionadas junto al código.

Cada ficha es un JSON en ``app/agente/fichas/`` cuyo nombre de archivo es el código del
cultivo (``papa.json`` → ``papa``). No hay base de datos ni red de por medio: la ficha
curada es la primera parada del camino híbrido (S7), la que responde rápido y de forma
verificable. Las fichas de cultivos que **no** están en el catálogo sembrado (``quinoa``,
``zapallo``) existen para probar ese camino sin inventar datos.

Por qué se descarta una ficha inválida en vez de romper el arranque: este módulo se
importa al levantar la API y desde el propio servicio del agente. Un JSON roto, un color
mal formado o una demanda fuera de dominio no son un problema del usuario ni del
proyecto que está calculando riego; abortar el import tumbaría toda la app por un curado
que se corrige en un commit. Se registra un ``warning`` con el archivo y el motivo, se
sigue con el resto de las fichas y el nombre afectado cae al respaldo web en lugar de
mentir con datos parciales.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.agente.cliente import FuenteRecuperada
from app.agente.validacion import normalizar

logger = logging.getLogger(__name__)

DIRECTORIO_FICHAS = Path(__file__).resolve().parent / "fichas"

DEMANDA_MAXIMA = 20.0
CICLO_MINIMO, CICLO_MAXIMO = 1, 730
PATRON_CODIGO = re.compile(r"^[a-z0-9_]{2,30}$")
PATRON_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
TIPOS_FUENTE = ("web", "catalogo_interno", "norma", "manual")


@dataclass(slots=True)
class FichaCultivo:
    """Ficha curada de un cultivo, lista para alimentar la recomendación."""

    codigo: str
    nombre: str
    icono: str
    color: str
    demanda_agua_l_m2_dia: float
    ciclo_dias: int
    meses_siembra: list[int] | None
    notas: str
    fuentes: list[FuenteRecuperada]
    # Datos agronómicos del paso 2. Opcionales: una ficha vieja sigue siendo válida.
    kc: float | None = None
    densidad_plantas_m2: float | None = None
    profundidad_raiz_cm: int | None = None
    # {"franco": {"veredicto": "apto", "motivo": "...", "fuente": "..."}}
    aptitud_suelo: dict[str, dict] | None = None
    # Imagen curada del cultivo y la página de donde salió (S4). Una ficha vieja sin
    # estas claves sigue siendo válida: el agente investiga la que falte.
    imagen: str | None = None
    imagen_fuente: str | None = None
    # Atribución obligatoria de la licencia de la foto. Texto libre, puede faltar en
    # una ficha vieja; las curadas lo traen y un test lo exige.
    imagen_credito: str | None = None


def _texto(valor: Any) -> str | None:
    if not isinstance(valor, str):
        return None
    limpio = valor.strip()
    return limpio or None


def _numero(valor: Any) -> float | None:
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    return None


VEREDICTOS_SUELO = ("apto", "condicionado", "no_apto")
KC_MAXIMO = 2.0
DENSIDAD_MAXIMA = 500.0
PROFUNDIDAD_MAXIMA = 300


def _aptitud_suelo(valor: Any) -> dict[str, dict] | None | bool:
    """Normaliza el mapa de aptitud por suelo. ``False`` = ficha mal formada."""

    if valor is None:
        return None
    if not isinstance(valor, dict):
        return False
    normalizado: dict[str, dict] = {}
    for suelo, datos in valor.items():
        if not isinstance(suelo, str) or not PATRON_CODIGO.match(suelo):
            return False
        if not isinstance(datos, dict):
            return False
        veredicto = datos.get("veredicto")
        if veredicto not in VEREDICTOS_SUELO:
            return False
        normalizado[suelo] = {
            "veredicto": veredicto,
            "motivo": _texto(datos.get("motivo")),
            "fuente": _texto(datos.get("fuente")),
        }
    return normalizado


def _meses(valor: Any) -> list[int] | None | bool:
    """Devuelve los meses válidos o ``False`` si el campo está mal formado.

    ``None`` significa "el cultivo no declara meses"; ``False`` es un error de la ficha.
    """

    if valor is None:
        return None
    if not isinstance(valor, list) or not valor:
        return False
    meses: set[int] = set()
    for item in valor:
        if isinstance(item, bool) or not isinstance(item, int):
            return False
        if not 1 <= item <= 12:
            return False
        meses.add(item)
    return sorted(meses)


def _url_http(valor: Any) -> str | None | bool:
    """URL absoluta http(s), ``None`` si no está y ``False`` si está mal formada."""

    if valor is None:
        return None
    texto = _texto(valor)
    if texto is None:
        return False
    partes = urlparse(texto)
    if partes.scheme not in ("http", "https") or not partes.netloc:
        return False
    return texto


def _fuentes(valor: Any) -> list[FuenteRecuperada] | None:
    if not isinstance(valor, list) or not valor:
        return None
    fuentes: list[FuenteRecuperada] = []
    for item in valor:
        if not isinstance(item, dict):
            return None
        tipo = _texto(item.get("tipo"))
        if tipo is None or tipo not in TIPOS_FUENTE:
            return None
        fuentes.append(
            FuenteRecuperada(
                tipo=tipo,
                titulo=_texto(item.get("titulo")),
                url=_texto(item.get("url")),
                fragmento=_texto(item.get("fragmento")),
            )
        )
    return fuentes


def _ficha_desde_datos(datos: Any, codigo_archivo: str) -> FichaCultivo | str:
    """Arma la ficha o devuelve el motivo por el que se descarta."""

    if not isinstance(datos, dict):
        return "el JSON no es un objeto"

    codigo = _texto(datos.get("codigo"))
    if codigo is None or not PATRON_CODIGO.match(codigo):
        return "código ausente o fuera del patrón [a-z0-9_]{2,30}"
    if codigo != codigo_archivo:
        return f"el código {codigo!r} no coincide con el archivo {codigo_archivo!r}"

    nombre = _texto(datos.get("nombre"))
    if nombre is None:
        return "nombre ausente"

    icono = _texto(datos.get("icono"))
    if icono is None:
        return "icono ausente"

    color = _texto(datos.get("color"))
    if color is None or not PATRON_COLOR.match(color):
        return "color ausente o fuera del formato #RRGGBB"

    demanda = _numero(datos.get("demanda_agua_l_m2_dia"))
    if demanda is None or not 0 < demanda <= DEMANDA_MAXIMA:
        return f"demanda fuera del dominio (0, {DEMANDA_MAXIMA:g}]"

    ciclo = _numero(datos.get("ciclo_dias"))
    if ciclo is None or not CICLO_MINIMO <= ciclo <= CICLO_MAXIMO:
        return f"ciclo fuera del dominio [{CICLO_MINIMO}, {CICLO_MAXIMO}]"

    meses = _meses(datos.get("meses_siembra"))
    if meses is False:
        return "meses_siembra debe ser una lista no vacía de enteros 1..12"

    fuentes = _fuentes(datos.get("fuentes"))
    if fuentes is None:
        return "fuentes ausente o con un tipo no permitido"

    kc = _numero(datos.get("kc"))
    if kc is not None and not 0 < kc <= KC_MAXIMO:
        return f"kc fuera del dominio (0, {KC_MAXIMO:g}]"

    densidad = _numero(datos.get("densidad_plantas_m2"))
    if densidad is not None and not 0 < densidad <= DENSIDAD_MAXIMA:
        return f"densidad_plantas_m2 fuera del dominio (0, {DENSIDAD_MAXIMA:g}]"

    profundidad = _numero(datos.get("profundidad_raiz_cm"))
    if profundidad is not None and not 1 <= profundidad <= PROFUNDIDAD_MAXIMA:
        return f"profundidad_raiz_cm fuera del dominio [1, {PROFUNDIDAD_MAXIMA}]"

    aptitud = _aptitud_suelo(datos.get("aptitud_suelo"))
    if aptitud is False:
        return (
            "aptitud_suelo debe ser un objeto código_de_suelo → "
            f"{{veredicto ∈ {VEREDICTOS_SUELO}, motivo}}"
        )

    imagen = _url_http(datos.get("imagen"))
    if imagen is False:
        return "imagen debe ser una URL http(s) absoluta o null"

    imagen_fuente = _url_http(datos.get("imagen_fuente"))
    if imagen_fuente is False:
        return "imagen_fuente debe ser una URL http(s) absoluta o null"

    imagen_credito = _texto(datos.get("imagen_credito"))

    notas = _texto(datos.get("notas")) or ""

    return FichaCultivo(
        kc=kc,
        densidad_plantas_m2=densidad,
        profundidad_raiz_cm=int(profundidad) if profundidad is not None else None,
        aptitud_suelo=aptitud or None,
        imagen=imagen,
        imagen_fuente=imagen_fuente,
        imagen_credito=imagen_credito,
        codigo=codigo,
        nombre=nombre,
        icono=icono,
        color=color.upper(),
        demanda_agua_l_m2_dia=demanda,
        ciclo_dias=int(ciclo),
        meses_siembra=meses,
        notas=notas,
        fuentes=fuentes,
    )


@lru_cache(maxsize=1)
def _cargar() -> tuple[FichaCultivo, ...]:
    """Lee y valida todas las fichas una sola vez, ordenadas por código."""

    if not DIRECTORIO_FICHAS.is_dir():
        logger.warning("No existe el directorio de fichas curadas: %s", DIRECTORIO_FICHAS)
        return ()

    fichas: list[FichaCultivo] = []
    for ruta in sorted(DIRECTORIO_FICHAS.glob("*.json")):
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Ficha descartada %s: no se pudo leer (%s)", ruta.name, exc)
            continue
        ficha = _ficha_desde_datos(datos, ruta.stem)
        if isinstance(ficha, str):
            logger.warning("Ficha descartada %s: %s", ruta.name, ficha)
            continue
        fichas.append(ficha)

    fichas.sort(key=lambda ficha: ficha.codigo)
    return tuple(fichas)


def listar() -> list[FichaCultivo]:
    """Todas las fichas curadas válidas, ordenadas por código."""

    return list(_cargar())


def buscar(nombre: str) -> FichaCultivo | None:
    """Busca una ficha por código o por nombre, sin acentos ni mayúsculas."""

    buscado = normalizar(nombre or "")
    if not buscado:
        return None
    for ficha in _cargar():
        if buscado in (normalizar(ficha.codigo), normalizar(ficha.nombre)):
            return ficha
    return None
