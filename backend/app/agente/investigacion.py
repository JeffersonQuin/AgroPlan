"""Investigación de un producto fuera del catálogo: híbrido ficha curada + web.

Camino de ``S7``:

1. Si hay ficha curada en :mod:`app.agente.fichas`, esa manda: cero red, cero costo.
2. Si no hay ficha, se consulta la web con un buscador inyectable (``busqueda_web``) y
   un presupuesto de ``AGENTE_MAX_BUSQUEDAS`` consultas por corrida.
3. Lo que vuelve se sanea antes de tocar nada: la web **sólo** puede aportar la ficha
   agronómica (demanda de agua, ciclo, meses de siembra). Caudal, separaciones, bomba y
   sectores siguen saliendo del motor determinístico y de los ``CHECK`` de la base
   (``S8``). Si no hay demanda y ciclo utilizables, no hay producto: se lanza
   :class:`ProductoNoReconocido` en lugar de inventar.

El adaptador real importa ``agno`` de forma diferida (igual que
:mod:`app.agente.cliente`): sin el paquete o sin ``AGENTE_API_KEY`` el import del módulo
no se rompe y la investigación falla con un mensaje claro.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from app.agente.cliente import FuenteRecuperada
from app.agente.fichas import FichaCultivo, buscar, normalizar
from app.core.config import settings

logger = logging.getLogger(__name__)

DEMANDA_MAXIMA = 20.0
CICLO_MINIMO, CICLO_MAXIMO = 1, 730
COLOR_POR_DEFECTO = "#4CAF50"
FRAGMENTO_MAX = 500
NOTAS_MAX = 500
# Anchos reales de la tabla `cultivos`: lo investigado no puede excederlos.
NOMBRE_MAX = 60
PATRON_CODIGO = re.compile(r"^[a-z0-9_]{2,30}$")
PATRON_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Consultas del presupuesto: cada reintento afina el pedido en vez de repetirlo.
CONSULTAS = (
    "ficha agronómica de {nombre}: demanda de agua en L/m2/día y ciclo en días",
    "{nombre}: requerimiento hídrico diario por metro cuadrado y duración del ciclo",
    "{nombre}: meses de siembra, agua diaria y ciclo del cultivo con fuente citada",
)

INSTRUCCIONES_BUSQUEDA = (
    "Buscás fichas agronómicas públicas de cultivos. Devolvés EXCLUSIVAMENTE un JSON "
    'con la forma {"nombre": str|null, "demanda_agua_l_m2_dia": number|null, '
    '"ciclo_dias": number|null, "meses_siembra": [int], "notas": str|null, '
    '"resultados": [{"titulo": str, "url": str, "fragmento": str}]}. '
    "No inventes valores: si una fuente no lo dice, usá null. Cada valor debe estar "
    "respaldado por una URL real."
)


class ProductoNoReconocido(Exception):
    """No hay ficha curada ni dato web verificable para el producto pedido."""


class InvestigacionError(Exception):
    """La búsqueda web falló técnicamente: el llamador decide cómo degradar."""


@dataclass(slots=True)
class Investigacion:
    """Ficha agronómica resuelta, con su origen y el costo real de la investigación."""

    codigo: str
    nombre: str
    icono: str
    color: str
    demanda_agua_l_m2_dia: float
    ciclo_dias: int
    meses_siembra: list[int] | None
    notas: str
    fuentes: list[FuenteRecuperada]
    origen: Literal["ficha", "web"]
    busquedas: int
    kc: float | None = None
    densidad_plantas_m2: float | None = None
    profundidad_raiz_cm: int | None = None
    aptitud_suelo: dict[str, dict] | None = None


# --------------------------------------------------------------------------- #
# Saneo de dominios
# --------------------------------------------------------------------------- #


def _numero(valor: Any) -> float | None:
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        encontrado = re.search(r"-?\d+(?:[.,]\d+)?", valor)
        if encontrado is not None:
            return float(encontrado.group(0).replace(",", "."))
    return None


def _demanda(valor: Any) -> float | None:
    """Demanda en (0, 20] L/m²/día; lo que se pasa del techo se recorta, lo absurdo no."""

    numero = _numero(valor)
    if numero is None or numero <= 0:
        return None
    return round(min(numero, DEMANDA_MAXIMA), 3)


def _ciclo(valor: Any) -> int | None:
    """Ciclo en [1, 730] días; no positivo no es dato utilizable."""

    numero = _numero(valor)
    if numero is None or numero <= 0:
        return None
    return max(CICLO_MINIMO, min(round(numero), CICLO_MAXIMO))


def _meses(valor: Any) -> list[int] | None:
    if valor is None:
        return None
    if isinstance(valor, str):
        candidatos: list[Any] = re.findall(r"\d+", valor)
    elif isinstance(valor, (list, tuple, set)):
        candidatos = list(valor)
    else:
        return None
    meses = {
        int(item)
        for item in candidatos
        if str(item).strip().isdigit() and 1 <= int(item) <= 12
    }
    return sorted(meses) or None


KC_MAXIMO = 2.0
DENSIDAD_MAXIMA = 500.0
PROFUNDIDAD_MAXIMA = 300
VEREDICTOS_SUELO = ("apto", "condicionado", "no_apto")


def _kc(valor: Any) -> float | None:
    numero = _numero(valor)
    if numero is None or not 0 < numero <= KC_MAXIMO:
        return None
    return round(numero, 2)


def _opcional_positivo(valor: Any, maximo: float) -> float | None:
    numero = _numero(valor)
    if numero is None or not 0 < numero <= maximo:
        return None
    return round(numero, 2)


def _entero_positivo(valor: Any, maximo: int) -> int | None:
    numero = _numero(valor)
    if numero is None or not 1 <= numero <= maximo:
        return None
    return int(numero)


def _aptitud(valor: Any) -> dict[str, dict] | None:
    """Saneo del mapa suelo → veredicto. Lo que no encaja se descarta, no se inventa."""

    if not isinstance(valor, dict):
        return None
    normalizado: dict[str, dict] = {}
    for suelo, datos in valor.items():
        if not isinstance(suelo, str) or not isinstance(datos, dict):
            continue
        if datos.get("veredicto") not in VEREDICTOS_SUELO:
            continue
        normalizado[suelo[:20]] = {
            "veredicto": datos["veredicto"],
            "motivo": (_texto(datos.get("motivo")) or "")[:200] or None,
            "fuente": (_texto(datos.get("fuente")) or "")[:120] or None,
        }
    return normalizado or None


def _color(valor: Any) -> str:
    if isinstance(valor, str) and PATRON_COLOR.match(valor.strip()):
        return valor.strip().upper()
    return COLOR_POR_DEFECTO


def _icono(nombre: str) -> str:
    for caracter in normalizar(nombre):
        if caracter.isalnum():
            return caracter.upper()
    return "?"


def _slug(nombre: str) -> str | None:
    base = re.sub(r"[^a-z0-9]+", "_", normalizar(nombre)).strip("_")
    base = re.sub(r"_+", "_", base)[:30].strip("_")
    return base if PATRON_CODIGO.match(base) else None


def _fragmento(resultado: dict[str, Any]) -> str | None:
    valor = _texto(
        resultado.get("fragmento")
        or resultado.get("snippet")
        or resultado.get("extracto")
        or resultado.get("texto")
        or resultado.get("contenido")
    )
    return valor[:FRAGMENTO_MAX] if valor else None


def _texto(valor: Any) -> str | None:
    if not isinstance(valor, str):
        return None
    limpio = valor.strip()
    return limpio or None


def _url(resultado: dict[str, Any]) -> str | None:
    valor = _texto(resultado.get("url") or resultado.get("link") or resultado.get("href"))
    if valor is None or not valor.lower().startswith(("http://", "https://")):
        return None
    return valor


def _resultados(respuesta: Any) -> list[dict[str, Any]]:
    """Normaliza lo que devuelve el buscador (o el modelo) a una lista de resultados."""

    if isinstance(respuesta, dict):
        for clave in ("resultados", "fuentes", "items", "results"):
            if isinstance(respuesta.get(clave), list):
                respuesta = respuesta[clave]
                break
        else:
            respuesta = [respuesta]
    if not isinstance(respuesta, (list, tuple)):
        return []
    return [item for item in respuesta if isinstance(item, dict)]


def _campos(resultado: dict[str, Any]) -> dict[str, Any]:
    """Campos agronómicos de un resultado, con sus alias habituales."""

    return {
        "nombre": _texto(resultado.get("nombre") or resultado.get("nombre_comun")),
        "demanda": resultado.get("demanda_agua_l_m2_dia")
        or resultado.get("demanda_l_m2_dia")
        or resultado.get("demanda_agua")
        or resultado.get("demanda"),
        "ciclo": resultado.get("ciclo_dias")
        or resultado.get("duracion_ciclo_dias")
        or resultado.get("ciclo"),
        "meses": resultado.get("meses_siembra") or resultado.get("meses"),
        "notas": _texto(
            resultado.get("notas") or resultado.get("descripcion") or resultado.get("resumen")
        ),
        "color": resultado.get("color"),
    }


def _acumular(acumulado: dict[str, Any], resultado: dict[str, Any]) -> None:
    for clave, valor in _campos(resultado).items():
        if acumulado.get(clave) is None and valor not in (None, "", []):
            acumulado[clave] = valor


# --------------------------------------------------------------------------- #
# Adaptadores
# --------------------------------------------------------------------------- #


def _contenido(respuesta: Any) -> Any:
    contenido = getattr(respuesta, "content", None)
    if isinstance(contenido, (list, dict)):
        return contenido
    if isinstance(contenido, str):
        try:
            return json.loads(contenido)
        except json.JSONDecodeError:
            logger.warning("La búsqueda web devolvió contenido no-JSON: %r", contenido[:200])
            return []
    return []


def _construir_buscador() -> Callable[[str], list[dict[str, Any]]]:
    """Buscador real: Agno contra el gateway configurado. Sin paquete o clave, no hay."""

    if not settings.AGENTE_API_KEY:
        raise ProductoNoReconocido(
            "No hay ficha curada para el producto y falta AGENTE_API_KEY: no se puede "
            "investigar en la web sin inventar datos."
        )

    try:
        from agno.agent import Agent
        from agno.models.openai.like import OpenAILike
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise ProductoNoReconocido(
            "No hay ficha curada para el producto y agno no está instalado: agregalo con "
            "`uv add 'agno>=3.2,<4'` o cargá una ficha curada."
        ) from exc

    modelo = OpenAILike(
        id=settings.AGENTE_MODELO,
        api_key=settings.AGENTE_API_KEY,
        base_url=settings.AGENTE_BASE_URL,
        timeout=settings.AGENTE_TIMEOUT_S,
    )
    agente = Agent(  # pragma: no cover - depende de red/credenciales
        model=modelo,
        description="Buscador de fichas agronómicas con cita de fuentes.",
        instructions=INSTRUCCIONES_BUSQUEDA,
        use_json_mode=True,
    )

    def buscar_web(consulta: str) -> list[dict[str, Any]]:  # pragma: no cover - red
        return _resultados(_contenido(agente.run(consulta)))

    return buscar_web


def _consulta(nombre: str, intento: int) -> str:
    plantilla = CONSULTAS[min(intento, len(CONSULTAS) - 1)]
    return plantilla.format(nombre=nombre)


# --------------------------------------------------------------------------- #
# Punto de entrada
# --------------------------------------------------------------------------- #


def _desde_ficha(ficha: FichaCultivo) -> Investigacion:
    return Investigacion(
        codigo=ficha.codigo,
        nombre=ficha.nombre,
        icono=ficha.icono,
        color=ficha.color,
        demanda_agua_l_m2_dia=ficha.demanda_agua_l_m2_dia,
        ciclo_dias=ficha.ciclo_dias,
        meses_siembra=list(ficha.meses_siembra) if ficha.meses_siembra else None,
        notas=ficha.notas,
        fuentes=list(ficha.fuentes),
        origen="ficha",
        busquedas=0,
        kc=ficha.kc,
        densidad_plantas_m2=ficha.densidad_plantas_m2,
        profundidad_raiz_cm=ficha.profundidad_raiz_cm,
        aptitud_suelo=dict(ficha.aptitud_suelo) if ficha.aptitud_suelo else None,
    )


def _fila_catalogo(catalogo: list[dict], codigo: str) -> dict | None:
    for fila in catalogo or []:
        if not isinstance(fila, dict):
            continue
        existente = _texto(fila.get("codigo"))
        if existente is not None and normalizar(existente) == codigo:
            return fila
    return None


def _desde_catalogo(
    fila: dict,
    *,
    codigo: str,
    nombre: str,
    acumulado: dict[str, Any],
    fuentes: list[FuenteRecuperada],
    busquedas: int,
) -> Investigacion:
    """Reusa la fila ya existente en el catálogo en vez de duplicar el cultivo."""

    demanda = _demanda(fila.get("demanda_agua_l_m2_dia")) or _demanda(acumulado.get("demanda"))
    ciclo = _ciclo(fila.get("ciclo_dias")) or _ciclo(acumulado.get("ciclo"))
    if demanda is None or ciclo is None:
        raise ProductoNoReconocido(
            f"El catálogo ya tiene {codigo!r} pero su ficha está incompleta: completala "
            "antes de usarlo."
        )
    nombre_fila = (_texto(fila.get("nombre")) or nombre)[:NOMBRE_MAX]
    return Investigacion(
        codigo=codigo,
        nombre=nombre_fila,
        icono=_texto(fila.get("icono")) or _icono(nombre_fila),
        color=_color(fila.get("color")),
        demanda_agua_l_m2_dia=demanda,
        ciclo_dias=ciclo,
        meses_siembra=_meses(fila.get("meses_siembra")) or _meses(acumulado.get("meses")),
        notas=(_texto(fila.get("notas")) or acumulado.get("notas") or "")[:NOTAS_MAX],
        fuentes=fuentes,
        origen="web",
        busquedas=busquedas,
        kc=_kc(fila.get("kc")) or _kc(acumulado.get("kc")),
        densidad_plantas_m2=(
            _opcional_positivo(fila.get("densidad_plantas_m2"), DENSIDAD_MAXIMA)
            or _opcional_positivo(acumulado.get("densidad"), DENSIDAD_MAXIMA)
        ),
        profundidad_raiz_cm=(
            _entero_positivo(fila.get("profundidad_raiz_cm"), PROFUNDIDAD_MAXIMA)
            or _entero_positivo(acumulado.get("profundidad"), PROFUNDIDAD_MAXIMA)
        ),
        aptitud_suelo=(
            _aptitud(fila.get("aptitud_suelo")) or _aptitud(acumulado.get("aptitud_suelo"))
        ),
    )


def _investigar_web(
    nombre: str,
    *,
    busqueda_web: Callable[[str], list[dict]],
    max_busquedas: int,
    catalogo: list[dict],
) -> Investigacion:
    acumulado: dict[str, Any] = {}
    fuentes: list[FuenteRecuperada] = []
    urls: set[str] = set()
    busquedas = 0

    for intento in range(max(int(max_busquedas), 0)):
        busquedas += 1
        try:
            respuesta = busqueda_web(_consulta(nombre, intento))
        except Exception as exc:
            raise InvestigacionError(
                f"La búsqueda web falló para {nombre!r}: {exc}"
            ) from exc

        for resultado in _resultados(respuesta):
            _acumular(acumulado, resultado)
            url = _url(resultado)
            if url is not None and url not in urls:
                urls.add(url)
                fuentes.append(
                    FuenteRecuperada(
                        tipo="web",
                        titulo=_texto(resultado.get("titulo") or resultado.get("title")) or url,
                        url=url,
                        fragmento=_fragmento(resultado),
                    )
                )

        if _demanda(acumulado.get("demanda")) is not None and (
            _ciclo(acumulado.get("ciclo")) is not None
        ):
            break

    demanda = _demanda(acumulado.get("demanda"))
    ciclo = _ciclo(acumulado.get("ciclo"))
    if demanda is None or ciclo is None:
        raise ProductoNoReconocido(
            f"No se encontraron datos agronómicos verificables (demanda de agua y ciclo) "
            f"para {nombre!r} en {busquedas} búsqueda(s) web."
        )

    nombre_resuelto = (_texto(acumulado.get("nombre")) or nombre)[:NOMBRE_MAX]
    codigo = _slug(nombre_resuelto)
    if codigo is None:
        raise ProductoNoReconocido(
            f"El nombre {nombre_resuelto!r} no permite derivar un código de cultivo válido."
        )

    fila = _fila_catalogo(catalogo, codigo)
    if fila is not None:
        return _desde_catalogo(
            fila,
            codigo=codigo,
            nombre=nombre_resuelto,
            acumulado=acumulado,
            fuentes=fuentes,
            busquedas=busquedas,
        )

    meses = _meses(acumulado.get("meses"))
    notas = acumulado.get("notas") or (fuentes[0].fragmento if fuentes else "") or ""
    return Investigacion(
        codigo=codigo,
        nombre=nombre_resuelto,
        icono=_icono(nombre_resuelto),
        color=_color(acumulado.get("color")),
        demanda_agua_l_m2_dia=demanda,
        ciclo_dias=ciclo,
        meses_siembra=meses,
        notas=notas[:NOTAS_MAX],
        fuentes=fuentes,
        origen="web",
        busquedas=busquedas,
        kc=_kc(acumulado.get("kc")),
        densidad_plantas_m2=_opcional_positivo(
            acumulado.get("densidad"), DENSIDAD_MAXIMA
        ),
        profundidad_raiz_cm=_entero_positivo(
            acumulado.get("profundidad"), PROFUNDIDAD_MAXIMA
        ),
        aptitud_suelo=_aptitud(acumulado.get("aptitud_suelo")),
    )


def investigar(
    nombre: str,
    *,
    catalogo: list[dict],
    busqueda_web: Callable[[str], list[dict]] | None = None,
    max_busquedas: int | None = None,
) -> Investigacion:
    """Resuelve la ficha agronómica de ``nombre``: curada primero, web de respaldo."""

    texto = (nombre or "").strip()
    if not texto:
        raise ProductoNoReconocido("El nombre del producto está vacío: nada que investigar.")

    ficha = buscar(texto)
    if ficha is not None:
        return _desde_ficha(ficha)

    buscador = busqueda_web if busqueda_web is not None else _construir_buscador()
    presupuesto = settings.AGENTE_MAX_BUSQUEDAS if max_busquedas is None else max_busquedas
    return _investigar_web(
        texto,
        busqueda_web=buscador,
        max_busquedas=presupuesto,
        catalogo=catalogo or [],
    )
