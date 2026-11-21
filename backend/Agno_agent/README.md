# Agente de recomendaciones

Este directorio ya no contiene lógica: el agente vive en `backend/app/agente/` y corre
embebido en el mismo FastAPI, no como proceso aparte.

- `app/agente/instrucciones.py` — prompt versionado (`PROMPT_VERSION`).
- `app/agente/cliente.py` — ejecución contra el gateway OpenAI-compatible y modo
  catálogo determinístico cuando no hay credenciales.
- `app/agente/validacion.py` — correcciones del backend antes de congelar la salida.

Variables de entorno (en `app/core/config.py`, ver `config.example.py`):
`AGENTE_BASE_URL`, `AGENTE_API_KEY`, `AGENTE_MODELO`, `AGENTE_TIMEOUT_S`,
`AGENTE_REINTENTOS`. Sin `AGENTE_API_KEY` el pipeline funciona igual en modo catálogo.

El flujo es `POST /proyectos/{id}/agente` → 202 → polling `GET /agente/corridas/{id}` →
`POST /proyectos/{id}/agente/corridas/{corrida_id}/aplicar`. El agente nunca escribe en
el proyecto.
