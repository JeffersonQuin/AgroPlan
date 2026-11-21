"""Agente de recomendaciones AgroPlan con acceso a la API del backend.

Los contratos de esta salida son un espejo estricto de ``app/schemas/agente.py``:
``PropuestaAgente`` no contiene geometría porque la API la deriva. El agente usa
``CustomApiTools`` para leer el proyecto, el terreno y los catálogos; el orquestador
aplica la propuesta con payloads válidos para ``BloqueCultivoCreate`` y
``SistemaRiegoIn`` (modelos ``proyecto_cultivo.py`` y ``riego.py``).

Variables de entorno:
    OPENCODE_API_KEY    clave del gateway (obligatoria)
    OPENCODE_BASE_URL   gateway OpenAI-compatible
    MODEL_ID            modelo a usar
    AGROPLAN_API_URL    base de la FastAPI, por defecto http://localhost:8000
    AGROPLAN_API_TOKEN  JWT de un usuario de AgroPlan (para los headers Bearer)
    PROYECTO_ID         UUID del proyecto (o primer argumento posicional)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Any, Literal

from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.tools.api import CustomApiTools
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

load_dotenv(Path(__file__).with_name(".env"))

# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #

MODEL_ID = os.getenv("MODEL_ID", "deepseek-v4.1-flash")
OPENCODE_BASE_URL = os.getenv(
    "OPENCODE_BASE_URL", "https://opencode.ai/inference/go/v1"
)
API_BASE_URL = os.getenv("AGROPLAN_API_URL", "http://localhost:8000").rstrip("/")
API_TOKEN = os.getenv("AGROPLAN_API_TOKEN") or None
SESSION_ID = os.getenv("AGNO_SESSION_ID", str(uuid.uuid4()))


# --------------------------------------------------------------------------- #
# Contratos espejo de app/schemas/ (Pydantic v2)
# --------------------------------------------------------------------------- #

FuenteAgua = Literal["pila", "pozo", "red", "cisterna", "tanque"]
OrigenCaudal = Literal["cliente", "asumido"]


class ProductoDeseado(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=2, max_length=60)
    prioridad: int = Field(default=1, ge=1, le=9)
    area_deseada_m2: float | None = Field(default=None, gt=0)


class EntradaAgente(BaseModel):
    """Igual que ``app.schemas.agente.EntradaAgente`` (huella incluida)."""

    model_config = ConfigDict(extra="forbid")

    proyecto_id: uuid.UUID
    productos: list[ProductoDeseado] = Field(min_length=1, max_length=8)
    area_m2: float = Field(gt=0)
    suelo_codigo: str = Field(min_length=2, max_length=20)
    fuente_agua: FuenteAgua
    caudal_efectivo_m3h: float = Field(gt=0, le=50)
    caudal_origen: OrigenCaudal
    zona: str | None = Field(default=None, max_length=120)
    pendiente_pct: float = Field(default=0, ge=0, le=30)

    def huella(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        normalizado = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()


class Advertencia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(max_length=40)
    mensaje: str = Field(max_length=300)
    bloqueante: bool = False
    campo: str | None = Field(default=None, max_length=40)


class CultivoRecomendado(BaseModel):
    """Espejo de ``CultivoRecomendado``: sin polígono, sin área calculada."""

    model_config = ConfigDict(extra="forbid")

    cultivo_codigo: str = Field(min_length=2, max_length=30)
    nombre: str = Field(min_length=2, max_length=60)
    color: str | None = Field(default=None, max_length=7)
    area_m2: float = Field(gt=0)
    demanda_l_m2_dia: float = Field(ge=0, le=20)
    ciclo_dias: int | None = Field(default=None, ge=1, le=730)
    siembra_sugerida: date | None = None
    cosecha_sugerida: date | None = None
    justificacion: str = Field(max_length=600)
    fuente_ids: list[int] = Field(default_factory=list)


class EmisorRecomendado(BaseModel):
    """Más estricto que el backend: solo valores que acepta el CHECK de la BD."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["gotero"] = "gotero"
    caudal_lh: Literal[2, 4, 8] = 2
    separacion_m: float = Field(default=0.3, ge=0.2, le=1.0)


class SistemaRecomendado(BaseModel):
    """Espejo de ``SistemaRecomendado`` con los dominios cerrados del backend."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["goteo", "aspersion", "inundacion"] = "goteo"
    emisor: EmisorRecomendado
    separacion_laterales_m: float = Field(gt=0, le=10)
    tanque_l: float | None = Field(default=None, gt=0)
    bomba_hp: Literal[0.5, 1, 1.5, 2] = 1
    num_sectores: int = Field(default=1, ge=1, le=8)


class PropuestaAgente(BaseModel):
    """Salida structured del agente; encaja con ``AgenteCorrida.salida``."""

    model_config = ConfigDict(extra="forbid")

    cultivos: list[CultivoRecomendado] = Field(min_length=1, max_length=8)
    sistema: SistemaRecomendado
    advertencias: list[Advertencia] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Respuesta del orquestador (no se persiste como ``salida``)
# --------------------------------------------------------------------------- #


class FuenteCitada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["web", "catalogo_interno", "norma", "manual"]
    titulo: str | None = None
    url: str | None = None
    fragmento: str | None = None


class LlamadaApi(BaseModel):
    endpoint: str
    method: str
    status_code: int | None = None
    ok: bool = False
    accion: Literal["lectura", "escritura"] = "lectura"


class RespuestaAgente(BaseModel):
    """Propuesta + evidencia de las llamadas API + payload listo para la corrida."""

    proyecto_id: uuid.UUID
    modelo: str
    session_id: str
    intake_hash: str
    propuesta: PropuestaAgente
    llamadas_api: list[LlamadaApi] = Field(default_factory=list)
    fuentes: list[FuenteCitada] = Field(default_factory=list)
    persistido: bool = False
    salida_corrida: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Cliente de la API (CustomApiTools)
# --------------------------------------------------------------------------- #


def construir_api_tools() -> CustomApiTools:
    return CustomApiTools(
        base_url=API_BASE_URL,
        api_key=API_TOKEN,
        headers={"Content-Type": "application/json"},
        timeout=30,
        enable_make_request=True,
    )


def _respuesta_api(crudo: str | dict[str, Any]) -> dict[str, Any]:
    return json.loads(crudo) if isinstance(crudo, str) else crudo


def _llamada(
    api: CustomApiTools,
    endpoint: str,
    *,
    method: str = "GET",
    json_data: dict[str, Any] | None = None,
    registro: list[LlamadaApi],
    accion: Literal["lectura", "escritura"] = "lectura",
    opcional: bool = False,
) -> dict[str, Any] | None:
    respuesta = _respuesta_api(
        api.make_request(endpoint=endpoint, method=method, json_data=json_data)
    )
    status = respuesta.get("status_code")
    ok = (
        isinstance(status, int)
        and 200 <= status < 300
        and "error" not in respuesta
    )
    registro.append(
        LlamadaApi(
            endpoint=endpoint,
            method=method,
            status_code=status,
            ok=ok,
            accion=accion,
        )
    )
    if not ok:
        if opcional:
            return None
        raise RuntimeError(
            f"API {method} {endpoint} -> HTTP {status}: "
            f"{respuesta.get('data') or respuesta.get('error')}"
        )
    dato = respuesta.get("data")
    return dato if isinstance(dato, dict) else {"items": dato}


def _obtener_contexto(
    api: CustomApiTools, proyecto_id: uuid.UUID, registro: list[LlamadaApi]
) -> dict[str, Any]:
    """Lee la fuente de verdad del proyecto antes de pedir recomendaciones."""

    proyecto = _llamada(api, f"/proyectos/{proyecto_id}", registro=registro)
    terreno = _llamada(api, f"/proyectos/{proyecto_id}/terreno", registro=registro)
    if proyecto is None or terreno is None:
        raise RuntimeError("El proyecto o su terreno no están disponibles")

    datos = _llamada(api, "/catalogos/cultivos", registro=registro) or {}
    cultivos = datos.get("items", []) if isinstance(datos, dict) else []
    suelos = _llamada(api, "/catalogos/suelos", registro=registro, opcional=True)
    bloques = _llamada(
        api, f"/proyectos/{proyecto_id}/cultivos", registro=registro, opcional=True
    )
    configuracion = _llamada(
        api, f"/proyectos/{proyecto_id}/riego", registro=registro, opcional=True
    )

    vertices = (terreno.get("geometria") or {}).get("vertices") or []
    xs = [float(vertice["x"]) for vertice in vertices]
    ys = [float(vertice["y"]) for vertice in vertices]
    punto_conexion = (
        {"x": round(min(xs), 2), "y": round(min(ys), 2)}
        if xs and ys
        else {"x": 0, "y": 0}
    )

    return {
        "proyecto": proyecto,
        "terreno": terreno,
        "cultivos": cultivos,
        "suelos": suelos or {},
        "bloques": (bloques or {}).get("items", []) if bloques else [],
        "configuracion": configuracion,
        "punto_conexion": punto_conexion,
    }


# --------------------------------------------------------------------------- #
# Prompt y ejecución del agente
# --------------------------------------------------------------------------- #


def _prompt(proyecto_id: uuid.UUID, contexto: dict[str, Any]) -> str:
    terreno = contexto["terreno"]
    proyecto = contexto["proyecto"]
    vertices = (terreno.get("geometria") or {}).get("vertices") or []
    xs = [float(vertice["x"]) for vertice in vertices]
    ys = [float(vertice["y"]) for vertice in vertices]
    resumen = {
        "proyecto": {
            "id": str(proyecto_id),
            "nombre": proyecto.get("nombre"),
            "zona": proyecto.get("zona"),
        },
        "terreno": {
            "area_m2": terreno.get("area_m2"),
            "suelo_codigo": terreno.get("suelo_codigo"),
            "fuente_agua": terreno.get("fuente_agua"),
            "caudal_efectivo_m3h": terreno.get("caudal_efectivo_m3h"),
            "caudal_origen": terreno.get("caudal_origen"),
            "pendiente_pct": terreno.get("pendiente_pct"),
            "bbox_m": {
                "x_min": min(xs) if xs else 0,
                "x_max": max(xs) if xs else 0,
                "y_min": min(ys) if ys else 0,
                "y_max": max(ys) if ys else 0,
            },
        },
        "catalogo_cultivos": contexto["cultivos"],
        "suelo": contexto["suelos"],
        "bloques_existentes": len(contexto["bloques"]),
        "configuracion_riego_actual": contexto["configuracion"],
    }
    return (
        "Analiza este proyecto de AgroPlan y entrega un plan de cultivo y riego.\n"
        "El contexto ya fue leído de la API con CustomApiTools; puedes volver a "
        "consultar make_request si necesitas verificar algún dato.\n\n"
        + json.dumps(resumen, ensure_ascii=False, indent=2)
        + "\n\nReglas obligatorias:\n"
        "- Usa solo cultivo_codigo del catálogo; nunca inventes códigos ni colores.\n"
        "- La suma de area_m2 de los cultivos no debe superar el area_m2 del terreno.\n"
        "- area_m2 es la INTENCIÓN de reparto; no devuelvas polígonos, sectores ni red.\n"
        "- bomba_hp solo 0.5, 1, 1.5 o 2; emisor.caudal_lh solo 2, 4 u 8.\n"
        "- emisor.separacion_m entre 0.2 y 1.0; separacion_laterales_m entre 0.5 y 10.\n"
        "- num_sectores entre 1 y 8; fuente de agua y punto de conexión los resuelve "
        "el orquestador a partir del terreno.\n"
        "- Si falta información, declárala en advertencias; no la inventes.\n"
        "- Responde siempre con el esquema estructurado PropuestaAgente, en español."
    )


def construir_agente(api_tools: CustomApiTools) -> Agent:
    api_key = os.getenv("OPENCODE_API_KEY")
    if not api_key:
        raise RuntimeError("Falta OPENCODE_API_KEY en el entorno")

    return Agent(
        model=OpenAILike(
            id=MODEL_ID,
            api_key=api_key,
            base_url=OPENCODE_BASE_URL,
            default_headers={
                "x-opencode-session": SESSION_ID,
                "User-Agent": "agro-recomendaciones/2.0",
            },
            timeout=90,
            max_retries=1,
        ),
        description=(
            "Agrónomo especialista en suelos, selección de cultivos y riego "
            "que consulta la API de AgroPlan antes de recomendar."
        ),
        instructions=[
            "Los códigos de cultivo y suelo salen del catálogo de la API.",
            "El terreno es la única fuente de verdad para área, suelo y caudal.",
            "Nunca devuelvas geometría: el motor determinístico la calcula.",
            "Cita solo fuentes reales; las del catálogo interno son suficientes.",
            "Responde en español con el esquema estructurado.",
        ],
        tools=[api_tools],
        output_schema=PropuestaAgente,
        use_json_mode=True,
        debug_mode=os.getenv("DEBUG") == "1",
    )


def _propuesta_desde_respuesta(contenido: Any) -> PropuestaAgente:
    if isinstance(contenido, PropuestaAgente):
        return contenido
    if isinstance(contenido, dict):
        return PropuestaAgente.model_validate(contenido)
    raise ValueError(f"Se esperaba PropuestaAgente, llegó: {contenido!r}")


# --------------------------------------------------------------------------- #
# Aplicación de la propuesta y armado de la respuesta
# --------------------------------------------------------------------------- #


def _fuentes(contexto: dict[str, Any]) -> list[FuenteCitada]:
    terreno = contexto["terreno"]
    return [
        FuenteCitada(
            tipo="catalogo_interno",
            titulo="Catálogo de cultivos AgroPlan",
            url=f"{API_BASE_URL}/catalogos/cultivos",
            fragmento=f"{len(contexto['cultivos'])} cultivos disponibles",
        ),
        FuenteCitada(
            tipo="catalogo_interno",
            titulo="Catálogo de suelos AgroPlan",
            url=f"{API_BASE_URL}/catalogos/suelos",
            fragmento=f"Suelo {terreno.get('suelo_codigo')}",
        ),
    ]


def _intake_hash(contexto: dict[str, Any], propuesta: PropuestaAgente) -> str:
    terreno = contexto["terreno"]
    proyecto = contexto["proyecto"]
    entrada = EntradaAgente(
        proyecto_id=uuid.UUID(str(proyecto["id"])),
        productos=[
            ProductoDeseado(
                nombre=cultivo.nombre,
                prioridad=indice + 1,
                area_deseada_m2=cultivo.area_m2,
            )
            for indice, cultivo in enumerate(propuesta.cultivos)
        ],
        area_m2=float(terreno["area_m2"]),
        suelo_codigo=str(terreno["suelo_codigo"]),
        fuente_agua=terreno["fuente_agua"],
        caudal_efectivo_m3h=float(terreno["caudal_efectivo_m3h"]),
        caudal_origen=terreno["caudal_origen"],
        zona=proyecto.get("zona"),
        pendiente_pct=float(terreno.get("pendiente_pct") or 0),
    )
    return entrada.huella()


def _aplicar_propuesta(
    api: CustomApiTools,
    proyecto_id: uuid.UUID,
    propuesta: PropuestaAgente,
    contexto: dict[str, Any],
    registro: list[LlamadaApi],
) -> bool:
    """Convierte la propuesta en llamadas válidas a los endpoints de escritura."""

    area_terreno = float(contexto["terreno"]["area_m2"])
    total = sum(cultivo.area_m2 for cultivo in propuesta.cultivos)
    if total > area_terreno + 0.01:
        raise RuntimeError(
            f"El área propuesta ({total:.2f} m²) supera el terreno "
            f"({area_terreno:.2f} m²)"
        )

    for cultivo in propuesta.cultivos:
        payload = {
            "cultivo_codigo": cultivo.cultivo_codigo,
            "etiqueta": cultivo.nombre,
            "siembra": (
                cultivo.siembra_sugerida.isoformat()
                if cultivo.siembra_sugerida
                else None
            ),
            "cosecha": (
                cultivo.cosecha_sugerida.isoformat()
                if cultivo.cosecha_sugerida
                else None
            ),
            "demanda_l_m2_dia": cultivo.demanda_l_m2_dia,
            "modo": "porcentaje",
            "porcentaje": round(cultivo.area_m2 / area_terreno * 100, 2),
        }
        _llamada(
            api,
            f"/proyectos/{proyecto_id}/cultivos",
            method="POST",
            json_data=payload,
            registro=registro,
            accion="escritura",
        )

    sistema = propuesta.sistema
    payload_riego = {
        "tipo": sistema.tipo,
        "fuente_agua": contexto["terreno"]["fuente_agua"],
        "tanque_l": sistema.tanque_l,
        "bomba_hp": sistema.bomba_hp,
        "diametro_principal_mm": 32,
        "emisor": sistema.emisor.model_dump(mode="json"),
        "separacion_laterales_m": sistema.separacion_laterales_m,
        "orientacion": "E-O",
        "punto_conexion": contexto["punto_conexion"],
        "num_sectores": sistema.num_sectores,
    }
    _llamada(
        api,
        f"/proyectos/{proyecto_id}/riego",
        method="PUT",
        json_data=payload_riego,
        registro=registro,
        accion="escritura",
    )
    # El motor determinístico materializa sectores y red. Si falla por hidráulica,
    # la propuesta sigue siendo válida: se reporta como advertencia.
    _llamada(
        api,
        f"/proyectos/{proyecto_id}/riego/generar",
        method="POST",
        registro=registro,
        accion="escritura",
        opcional=True,
    )
    return True


def _proyecto_id() -> uuid.UUID:
    crudo = sys.argv[1] if len(sys.argv) > 1 else os.getenv("PROYECTO_ID", "")
    if not crudo:
        raise SystemExit(
            "Indica el proyecto: python Agno_agent/main.py <proyecto_id> "
            "o exporta PROYECTO_ID=<uuid>"
        )
    try:
        return uuid.UUID(str(crudo))
    except ValueError as exc:
        raise SystemExit("PROYECTO_ID no es un UUID válido") from exc


def _imprimir(respuesta: RespuestaAgente) -> None:
    print("modelo:", respuesta.modelo)
    print("proyecto:", respuesta.proyecto_id)
    print("session:", respuesta.session_id)
    print("intake_hash:", respuesta.intake_hash)
    print("persistido_en_api:", respuesta.persistido)
    print("llamadas_api:")
    for llamada in respuesta.llamadas_api:
        estado = "OK" if llamada.ok else "ERROR"
        print(f"  {llamada.method} {llamada.endpoint} -> {llamada.status_code} {estado}")
    for cultivo in respuesta.propuesta.cultivos:
        print(
            f"- {cultivo.nombre} ({cultivo.cultivo_codigo}): "
            f"{cultivo.area_m2} m² (confianza vía justificación: {cultivo.justificacion})"
        )
    print("Riego:", json.dumps(respuesta.propuesta.sistema.model_dump(), ensure_ascii=False))
    print(
        "Advertencias:",
        json.dumps(
            [alerta.model_dump(mode="json") for alerta in respuesta.propuesta.advertencias],
            ensure_ascii=False,
        ),
    )
    print(
        "Fuentes:",
        json.dumps(
            [fuente.model_dump(mode="json") for fuente in respuesta.fuentes],
            ensure_ascii=False,
        ),
    )
    print("salida para AgenteCorrida.salida:")
    print(json.dumps(respuesta.salida_corrida, ensure_ascii=False, indent=2))


def main() -> RespuestaAgente:
    proyecto_id = _proyecto_id()
    api = construir_api_tools()
    registro: list[LlamadaApi] = []

    try:
        contexto = _obtener_contexto(api, proyecto_id, registro)
    except RuntimeError as exc:
        raise SystemExit(f"No se pudo cargar el proyecto desde la API: {exc}") from exc

    agente = construir_agente(api)
    respuesta_agno = agente.run(_prompt(proyecto_id, contexto))
    propuesta = _propuesta_desde_respuesta(respuesta_agno.content)

    fuentes = _fuentes(contexto)
    for cultivo in propuesta.cultivos:
        if not cultivo.fuente_ids:
            cultivo.fuente_ids = [1, 2]

    persistido = False
    if contexto["bloques"]:
        propuesta.advertencias.append(
            Advertencia(
                codigo="bloques_existentes",
                mensaje=(
                    "El proyecto ya tiene cultivos asignados: se devuelve la propuesta "
                    "pero no se crearon bloques para evitar duplicados."
                ),
                campo="cultivos",
            )
        )
    else:
        try:
            persistido = _aplicar_propuesta(
                api, proyecto_id, propuesta, contexto, registro
            )
        except RuntimeError as exc:
            propuesta.advertencias.append(
                Advertencia(
                    codigo="api_write_error",
                    mensaje=f"No se pudo aplicar la propuesta: {exc}"[:300],
                    bloqueante=True,
                )
            )

    respuesta = RespuestaAgente(
        proyecto_id=proyecto_id,
        modelo=MODEL_ID,
        session_id=SESSION_ID,
        intake_hash=_intake_hash(contexto, propuesta),
        propuesta=propuesta,
        llamadas_api=registro,
        fuentes=fuentes,
        persistido=persistido,
        salida_corrida=propuesta.model_dump(mode="json"),
    )
    _imprimir(respuesta)
    return respuesta


if __name__ == "__main__":
    main()
