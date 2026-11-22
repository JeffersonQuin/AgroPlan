"""Agente de recomendaciones AgroPlan embebido en el backend.

El agente **no** escribe en el proyecto ni calcula geometría: recibe el intake que ya
normalizó el servicio, devuelve una ``PropuestaAgente`` y el servicio la congela en
``agente_corridas.salida``. Los bloques y el riego se materializan recién cuando el
usuario confirma con ``POST /proyectos/{id}/agente/corridas/{corrida_id}/aplicar``.

Módulos:

* ``instrucciones`` — prompt versionado (``PROMPT_VERSION``) e instrucciones.
* ``validacion`` — correcciones determinísticas sobre la propuesta cruda del modelo.
* ``cliente`` — ejecución contra el gateway OpenAI-compatible, con modo catálogo
  determinístico cuando no hay credenciales.
"""

from app.agente.cliente import (
    ContextoAgente,
    ErrorAgente,
    FuenteRecuperada,
    ResultadoAgente,
    ejecutar,
)
from app.agente.instrucciones import PROMPT_VERSION

__all__ = [
    "PROMPT_VERSION",
    "ContextoAgente",
    "ErrorAgente",
    "FuenteRecuperada",
    "ResultadoAgente",
    "ejecutar",
]
