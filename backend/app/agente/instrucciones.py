"""Prompt e instrucciones del agente de recomendaciones.

``PROMPT_VERSION`` se congela en cada corrida: si mañana cambia el texto del prompt,
las corridas viejas siguen explicándose con la versión que las produjo.
"""

from __future__ import annotations

import json
from typing import Any

from app.schemas.agente import EntradaAgente

PROMPT_VERSION = "v1"

INSTRUCCIONES = [
    "Sos un agrónomo especialista en suelos, selección de cultivos y riego por goteo.",
    "Elegís cultivos del catálogo de AgroPlan; nunca inventás códigos, colores ni normas.",
    "El terreno y el intake son la única fuente de verdad para área, suelo y caudal.",
    "Nunca devolvés geometría, polígonos, sectores, red ni cantidades de materiales.",
    "``area_m2`` es la asignación que proponés, no un área calculada.",
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
) -> str:
    """Arma el mensaje con el intake congelado y el catálogo disponible."""

    contexto = {
        "intake": entrada.model_dump(mode="json", exclude_none=True),
        "siembra": entrada.siembra.isoformat() if entrada.siembra else None,
        "catalogo_cultivos": catalogo,
        "suelo": suelo,
        "bloques_existentes": bloques,
        "riego_actual": riego_actual,
    }
    return (
        "Analizá este proyecto de AgroPlan y proponé el reparto de cultivos y los "
        "parámetros de riego.\n\n"
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
        "(demanda de agua, profundidad de raíz, compatibilidad y rotación).\n"
        "- Investigá cada producto que no esté en el catálogo y devolvé su demanda de "
        "agua, su ciclo y una fecha aproximada de cosecha.\n"
        "- `siembra_sugerida` es la fecha de siembra del intake; `cosecha_sugerida` se "
        "calcula sumando el ciclo a esa siembra.\n"
        "- Citá en `fuentes` la información agronómica que usaste; si no hay fuente, "
        "no inventes el dato.\n"
        "- Justificá cada cultivo en menos de 600 caracteres, con criterio agronómico."
    )
