"""Ejecución del agente: gateway OpenAI-compatible con fallback determinístico.

Dos modos, misma salida validada:

* ``llm`` — Agno contra el gateway configurado (``AGENTE_BASE_URL``/``AGENTE_API_KEY``).
* ``catalogo`` — sin credenciales, el sistema arma la propuesta con el catálogo de
  cultivos, el caudal disponible y el intake. No es un adorno: es el fallback que
  sostiene la demo y los tests cuando no hay clave.

En ambos casos la propuesta pasa por ``validacion.corregir`` y por el contrato real
``app.schemas.agente.PropuestaAgente``: el agente nunca devuelve geometría.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import ValidationError

from app.agente import instrucciones
from app.agente.validacion import PropuestaInvalida, corregir, normalizar
from app.core.config import settings
from app.schemas.agente import (
    CultivoRecomendado,
    EmisorRecomendado,
    EntradaAgente,
    ProductoDeseado,
    PropuestaAgente,
    SistemaRecomendado,
)
from app.schemas.comun import Advertencia

ModoEjecucion = Literal["llm", "catalogo"]

MODO_CATALOGO_ADVERTENCIA = "AGENTE_SIN_CREDENCIALES"
PRODUCTO_NO_RECONOCIDO_ADVERTENCIA = "PRODUCTO_NO_RECONOCIDO"
JUSTIFICACION_CATALOGO = (
    "Elegido por el catálogo: demanda de {demanda:g} L/m²/día compatible con los "
    "{disponible:g} L/m²/día disponibles del caudal efectivo."
)


class ErrorAgente(Exception):
    """La corrida no se pudo completar: el servicio la marca como ``error``."""


@dataclass(slots=True)
class FuenteRecuperada:
    """Fuente citada durante la corrida, todavía sin id de base."""

    tipo: str
    titulo: str | None = None
    url: str | None = None
    fragmento: str | None = None


@dataclass(slots=True)
class ContextoAgente:
    """Todo lo que el agente puede mirar, ya leído de la base por el servicio."""

    entrada: EntradaAgente
    catalogo: list[dict[str, Any]] = field(default_factory=list)
    suelo: dict[str, Any] | None = None
    riego_actual: dict[str, Any] | None = None
    bloques: int = 0
    # Precios que ya investigó otra corrida y siguen vigentes (S6): viajan al prompt
    # para no gastar tokens buscándolos de nuevo.
    precios: list[dict[str, Any]] = field(default_factory=list)
    # El gateway OpenAI-compatible de OpenCode enruta por sesión: sin este id responde
    # 400 "missing x-opencode-session". Se usa el id de la corrida, que además sirve
    # para rastrear qué llamada produjo qué propuesta.
    sesion: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(slots=True)
class ResultadoAgente:
    propuesta: PropuestaAgente
    fuentes: list[FuenteRecuperada]
    modelo: str
    modo: ModoEjecucion
    tokens_entrada: int | None = None
    tokens_salida: int | None = None


# --------------------------------------------------------------------------- #
# Modo catálogo (determinístico)
# --------------------------------------------------------------------------- #

FUENTE_CATALOGO_CULTIVOS = FuenteRecuperada(
    tipo="catalogo_interno",
    titulo="Catálogo de cultivos AgroPlan",
    url="/catalogos/cultivos",
    fragmento="Demanda hídrica y ciclo por cultivo activo",
)
FUENTE_CATALOGO_SUELOS = FuenteRecuperada(
    tipo="catalogo_interno",
    titulo="Catálogo de suelos AgroPlan",
    url="/catalogos/suelos",
    fragmento="Aptitud del suelo informado en el terreno",
)


def _litros_por_m2_dia(entrada: EntradaAgente) -> float:
    return entrada.caudal_efectivo_m3h * 1000 / entrada.area_m2


def _numero_sectores(area_m2: float) -> int:
    if area_m2 <= 250:
        return 1
    if area_m2 <= 500:
        return 2
    if area_m2 <= 1000:
        return 4
    return 8


def _buscar_cultivo(
    producto: ProductoDeseado, catalogo: list[dict[str, Any]]
) -> dict[str, Any] | None:
    buscado = normalizar(producto.nombre)
    for cultivo in catalogo:
        if buscado in (normalizar(str(cultivo["codigo"])), normalizar(str(cultivo["nombre"]))):
            return cultivo
    return None


def _elegir_cultivos(
    entrada: EntradaAgente, catalogo: list[dict[str, Any]]
) -> tuple[list[tuple[dict[str, Any], float | None]], list[str]]:
    disponibles = _litros_por_m2_dia(entrada)
    elegidos: list[tuple[dict[str, Any], float | None]] = []
    no_reconocidos: list[str] = []
    usados: set[str] = set()

    for producto in sorted(entrada.productos, key=lambda item: item.prioridad):
        cultivo = _buscar_cultivo(producto, catalogo)
        if cultivo is None:
            # El producto pedido no está en el catálogo: no se reemplaza en silencio.
            no_reconocidos.append(producto.nombre)
            continue
        if str(cultivo["codigo"]) in usados:
            continue
        usados.add(str(cultivo["codigo"]))
        elegidos.append((cultivo, producto.area_deseada_m2))

    # Solo se completan los productos que el usuario pidió y no matchearon el
    # catálogo: proponer cultivos que nadie pidió sería inventar, no recomendar.
    cupo = min(8, len(catalogo), max(len(entrada.productos), 1))
    ordenados = sorted(
        catalogo,
        key=lambda cultivo: (
            float(cultivo.get("demanda_agua_l_m2_dia") or 0),
            str(cultivo["codigo"]),
        ),
    )
    for cultivo in ordenados:
        if len(elegidos) >= cupo:
            break
        codigo = str(cultivo["codigo"])
        if codigo in usados:
            continue
        demanda = float(cultivo.get("demanda_agua_l_m2_dia") or 0)
        if demanda > disponibles:
            continue
        usados.add(codigo)
        elegidos.append((cultivo, None))

    if not elegidos:
        elegidos.append((ordenados[0], None))
    return elegidos, no_reconocidos


def _propuesta_catalogo(contexto: ContextoAgente) -> tuple[PropuestaAgente, list[FuenteRecuperada]]:
    entrada = contexto.entrada
    if not contexto.catalogo:
        raise ErrorAgente("El catálogo de cultivos está vacío: no hay nada que recomendar")

    disponibles = _litros_por_m2_dia(entrada)
    elegidos, no_reconocidos = _elegir_cultivos(entrada, contexto.catalogo)
    area_reparto = entrada.area_m2 / len(elegidos)

    cultivos: list[CultivoRecomendado] = []
    for indice, (catalogo_cultivo, area_deseada) in enumerate(elegidos):
        demanda = float(catalogo_cultivo.get("demanda_agua_l_m2_dia") or 0)
        ciclo = catalogo_cultivo.get("ciclo_dias")
        cultivos.append(
            CultivoRecomendado(
                cultivo_codigo=str(catalogo_cultivo["codigo"]),
                nombre=str(catalogo_cultivo["nombre"]),
                color=catalogo_cultivo.get("color"),
                area_m2=round(area_deseada or area_reparto, 2),
                demanda_l_m2_dia=demanda,
                ciclo_dias=int(ciclo) if ciclo else None,
                justificacion=JUSTIFICACION_CATALOGO.format(
                    demanda=demanda, disponible=round(disponibles, 2)
                )[:600],
                fuente_ids=[indice + 1],
            )
        )

    propuesta = PropuestaAgente(
        cultivos=cultivos,
        sistema=SistemaRecomendado(
            tipo="goteo",
            emisor=EmisorRecomendado(tipo="gotero", caudal_lh=2, separacion_m=0.3),
            separacion_laterales_m=0.5,
            tanque_l=None,
            bomba_hp=1,
            num_sectores=_numero_sectores(entrada.area_m2),
        ),
        advertencias=[
            Advertencia(
                codigo=MODO_CATALOGO_ADVERTENCIA,
                mensaje=(
                    "La corrida se resolvió con el catálogo interno: "
                    + (
                        "AGENTE_MODO está en 'catalogo'."
                        if settings.AGENTE_MODO == "catalogo"
                        else "no hay credenciales del modelo configuradas."
                    )
                ),
                campo="modelo",
            )
        ]
        + [
            Advertencia(
                codigo=PRODUCTO_NO_RECONOCIDO_ADVERTENCIA,
                mensaje=(
                    f"'{nombre}' no está en el catálogo: se recomendó otro cultivo en su "
                    "lugar. Cargá la ficha o escribí el producto en el paso 2 para que el "
                    "agente lo investigue."
                )[:300],
                campo="productos",
            )
            for nombre in no_reconocidos
        ],
    )
    return propuesta, [FUENTE_CATALOGO_CULTIVOS, FUENTE_CATALOGO_SUELOS]


# --------------------------------------------------------------------------- #
# Modo LLM (Agno + gateway OpenAI-compatible)
# --------------------------------------------------------------------------- #


def _importar_agno() -> tuple[Any, Any]:
    try:
        from agno.agent import Agent
        from agno.models.openai.like import OpenAILike
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise ErrorAgente(
            "agno no está instalado: agregalo con `uv add 'agno>=3.2,<4'` o dejá "
            "AGENTE_API_KEY vacía para correr en modo catálogo"
        ) from exc
    return Agent, OpenAILike


def _tokens(respuesta: Any, nombre: str) -> int | None:
    metricas = getattr(respuesta, "metrics", None)
    valor = getattr(metricas, nombre, None) if metricas is not None else None
    return int(valor) if isinstance(valor, (int, float)) else None


def _propuesta_llm(contexto: ContextoAgente) -> tuple[PropuestaAgente, int | None, int | None]:
    Agent, OpenAILike = _importar_agno()

    modelo = OpenAILike(
        id=settings.AGENTE_MODELO,
        api_key=settings.AGENTE_API_KEY,
        base_url=settings.AGENTE_BASE_URL,
        timeout=settings.AGENTE_TIMEOUT_S,
        # Razonamiento bajo: el reparto se valida del lado del backend, no hace falta
        # que el modelo "piense" de más ni que gaste tokens en eso.
        reasoning_effort=settings.AGENTE_RAZONAMIENTO,
        default_headers={
            "x-opencode-session": contexto.sesion,
            "User-Agent": "agroplan-agente/1.0",
        },
    )
    agente = Agent(
        model=modelo,
        description=(
            "Agrónomo especialista en suelos, selección de cultivos y riego por goteo "
            "que propone repartos y parámetros de riego para un proyecto de AgroPlan."
        ),
        instructions=instrucciones.INSTRUCCIONES,
        output_schema=PropuestaAgente,
        use_json_mode=True,
    )

    mensaje = instrucciones.construir_mensaje(
        contexto.entrada,
        catalogo=contexto.catalogo,
        suelo=contexto.suelo,
        riego_actual=contexto.riego_actual,
        bloques=contexto.bloques,
        precios=contexto.precios,
    )

    intentos = 1 + max(settings.AGENTE_REINTENTOS, 0)
    ultimo_error: Exception | None = None
    for _ in range(intentos):
        respuesta = agente.run(mensaje)
        contenido = getattr(respuesta, "content", None)
        try:
            if isinstance(contenido, PropuestaAgente):
                return (
                    contenido,
                    _tokens(respuesta, "input_tokens"),
                    _tokens(respuesta, "output_tokens"),
                )
            if isinstance(contenido, dict):
                return (
                    PropuestaAgente.model_validate(contenido),
                    _tokens(respuesta, "input_tokens"),
                    _tokens(respuesta, "output_tokens"),
                )
            if isinstance(contenido, str):
                return (
                    PropuestaAgente.model_validate_json(contenido),
                    _tokens(respuesta, "input_tokens"),
                    _tokens(respuesta, "output_tokens"),
                )
            raise ValueError(f"Respuesta inesperada del modelo: {type(contenido)!r}")
        except (ValidationError, ValueError) as exc:
            # Solo se reintenta un error de validación; un timeout no se repite para
            # no duplicar el costo de la llamada.
            ultimo_error = exc

    detalle = str(ultimo_error)
    if "json_invalid" in detalle or "Invalid JSON" in detalle:
        detalle += (
            " | La respuesta llegó cortada o vacía: casi siempre es el timeout del "
            f"modelo ({settings.AGENTE_TIMEOUT_S} s) antes de terminar el JSON. "
            "Subí AGENTE_TIMEOUT_S en el entorno (por ejemplo 240)."
        )
    raise ErrorAgente(f"El modelo no devolvió una propuesta válida: {detalle}"[:2000])


# --------------------------------------------------------------------------- #
# Punto de entrada
# --------------------------------------------------------------------------- #


def ejecutar(contexto: ContextoAgente) -> ResultadoAgente:
    """Corre el agente y devuelve la propuesta ya corregida y validada."""

    catalogo_por_codigo = {
        str(cultivo["codigo"]): cultivo for cultivo in contexto.catalogo
    }

    usar_modelo = settings.AGENTE_MODO == "llm" and bool(settings.AGENTE_API_KEY)

    if usar_modelo:
        propuesta, tokens_entrada, tokens_salida = _propuesta_llm(contexto)
        fuentes = [
            FuenteRecuperada(
                tipo="catalogo_interno",
                titulo="Catálogo de cultivos AgroPlan",
                url="/catalogos/cultivos",
                fragmento="Catálogo entregado al modelo en el mensaje",
            )
        ]
        modelo = settings.AGENTE_MODELO
        modo: ModoEjecucion = "llm"
    else:
        propuesta, fuentes = _propuesta_catalogo(contexto)
        tokens_entrada = None
        tokens_salida = None
        modelo = "catalogo"
        modo = "catalogo"

    try:
        corregida = corregir(
            propuesta,
            catalogo=catalogo_por_codigo,
            area_m2=float(contexto.entrada.area_m2),
            total_fuentes=len(fuentes),
            siembra=contexto.entrada.siembra,
        )
    except PropuestaInvalida as exc:
        raise ErrorAgente(str(exc)) from exc

    return ResultadoAgente(
        propuesta=corregida,
        fuentes=fuentes,
        modelo=modelo,
        modo=modo,
        tokens_entrada=tokens_entrada,
        tokens_salida=tokens_salida,
    )


def area_por_sector(area_m2: float) -> int:  # pragma: no cover - compatibilidad
    return math.ceil(_numero_sectores(area_m2))
