"""Prompt e instrucciones del agente de recomendaciones.

``PROMPT_VERSION`` se congela en cada corrida: si mañana cambia el texto del prompt,
las corridas viejas siguen explicándose con la versión que las produjo.
"""

from __future__ import annotations

import json
from typing import Any

from app.schemas.agente import EntradaAgente

PROMPT_VERSION = "v4"

INSTRUCCIONES = [
    "Sos un agrónomo especialista en suelos, selección de cultivos y riego por goteo.",
    "Elegís cultivos del catálogo de AgroPlan; nunca inventás códigos, colores ni normas.",
    "El terreno y el intake son la única fuente de verdad para área, suelo y caudal.",
    (
        "Usás la ficha de cada producto (kc, aptitud de suelo, raíz, densidad y meses de "
        "siembra) y la del suelo (infiltración y retención); si un dato no está, lo omitís."
    ),
    "Nunca devolvés geometría, polígonos, sectores, red ni coordenadas.",
    "``area_m2`` es la asignación que proponés, no un área calculada.",
    (
        "Devolvés cifras operativas, materiales con precio y fuentes, recomendaciones e "
        "imágenes con su atribución; un dato ausente queda en null, nunca en cero."
    ),
    "Si falta un dato, lo declarás en ``advertencias``; no lo inventás.",
    "Respondés siempre con el esquema estructurado, en español.",
]


def construir_mensaje(
    entrada: EntradaAgente,
    *,
    catalogo: list[dict[str, Any]],
    suelo: dict[str, Any] | None,
    riego_actual: dict[str, Any] | None,
    bloques: int,
    precios: list[dict[str, Any]] | None = None,
) -> str:
    """Arma el mensaje con el intake congelado y el catálogo disponible."""

    contexto = {
        "intake": entrada.model_dump(mode="json", exclude_none=True),
        "siembra": entrada.siembra.isoformat() if entrada.siembra else None,
        "restricciones": (
            entrada.restricciones.model_dump(mode="json", exclude_none=True)
            if entrada.restricciones is not None
            else None
        ),
        "terreno": {
            "area_m2": entrada.area_m2,
            "pendiente_pct": entrada.pendiente_pct,
            "perimetro_m": entrada.perimetro_m,
            "lados_m": (
                [lado.model_dump(mode="json") for lado in entrada.lados_m]
                if entrada.lados_m
                else None
            ),
            "geometria": (
                entrada.geometria.model_dump(mode="json")
                if entrada.geometria is not None
                else None
            ),
            "profundidad_nivel_dinamico_m": entrada.profundidad_nivel_dinamico_m,
        },
        "catalogo_cultivos": catalogo,
        "suelo": suelo,
        "bloques_existentes": bloques,
        "riego_actual": riego_actual,
        # Precios ya investigados y todavía vigentes (S6): si el material está acá,
        # no hace falta volver a buscarlo en la web.
        "precios_conocidos": precios or [],
    }
    return (
        "Analizá este proyecto de AgroPlan y armá el informe del paso 4: reparto de "
        "cultivos, parámetros de riego, cifras hidráulicas, materiales con precios, "
        "recomendaciones e imágenes.\n\n"
        + json.dumps(contexto, ensure_ascii=False, indent=2, default=str)
        + "\n\nReglas obligatorias:\n"
        "- Usá solo ``cultivo_codigo`` del catálogo; el nombre, el color y la demanda "
        "los completa el backend desde el catálogo.\n"
        "- La suma de ``area_m2`` no puede superar el área del terreno.\n"
        "- ``bomba_hp`` ∈ {0.5, 1, 1.5, 2}; ``emisor.caudal_lh`` ∈ {2, 4, 8}; "
        "``emisor.separacion_m`` ∈ [0.2, 1.0].\n"
        "- ``separacion_laterales_m`` ∈ [0.5, 10]; ``num_sectores`` ∈ [1, 8].\n"
        "- Citá en ``fuente_ids`` solo índices de las fuentes recuperadas en esta "
        "corrida; el backend reemplaza lo que no exista.\n"
        "- Repartí **toda** el área del terreno entre los productos pedidos: la suma de "
        "`area_m2` tiene que dar el área del terreno, no menos.\n"
        "- El reparto tiene que ser el más eficiente para esos productos juntos "
        "(demanda de agua, ``kc``, profundidad de raíz, ``aptitud_suelo``, "
        "``meses_siembra``, compatibilidad y rotación).\n"
        "- Investigá cada producto que no esté en el catálogo y devolvé su demanda de "
        "agua, su ciclo y una fecha aproximada de cosecha.\n"
        "- `siembra_sugerida` es la fecha de siembra del intake; `cosecha_sugerida` se "
        "calcula sumando el ciclo a esa siembra.\n"
        "- Citá en `fuentes` la información agronómica que usaste; si no hay fuente, "
        "no inventes el dato.\n"
        "- Justificá cada cultivo en menos de 600 caracteres, con criterio agronómico.\n"
        "- Completá ``cifras``: presión de trabajo en bar, eficiencia en %, demanda "
        "pico en L/día, autonomía del tanque en días, tiempo de riego en horas y un "
        "turno por sector. Basate en el caudal efectivo, el área, la ficha de suelo "
        "(infiltración y retención) y las restricciones del paso 3. Un dato que no "
        "puedas fundamentar queda en null.\n"
        "- Completá ``materiales`` con rubro, descripción, cantidad, unidad, precio "
        "unitario y total en Bs y ``fuente_url``: la fuente tiene que ser una URL "
        "http(s) real de donde sacaste el precio. Si no encontrás precio, el campo "
        "queda en null; nunca lo inventes.\n"
        "- Si ``precios_conocidos`` trae un precio vigente para un material, usá ese "
        "precio, esa ``fuente_url`` y esa ``recuperado_en`` y no lo vuelvas a "
        "investigar; si no está o está vencido, buscalo en la web.\n"
        "- Completá ``recomendaciones`` con título, detalle y justificación, usando "
        "también las fichas y las restricciones (energía, tanque y presupuesto).\n"
        "- Imágenes (S4): si un producto del intake ya trae ``imagen_url`` de la ficha "
        "curada, usá esa imagen y devolvé ``imagen_url`` e ``imagen_fuente_url`` en "
        "null: no investigues otra. Si el producto no trae ``imagen_url`` y no está en "
        "``catalogo_cultivos``, investigá una imagen real y devolvé su URL http(s) con "
        "la página de donde salió en ``imagen_fuente_url``. Hacé lo mismo con el "
        "equipo de cabecera. Nunca inventes URLs."
    )
