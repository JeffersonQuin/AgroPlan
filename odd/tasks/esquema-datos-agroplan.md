# Esquema de datos AgroPlan (13 tablas nuevas)

Entrega del esquema de persistencia para el backend de AgroPlan: modelos SQLAlchemy 2.0,
schemas Pydantic v2, migración Alembic y catálogo sembrado. Sin endpoints, sin motor, sin agente.
Rama `feat/esquema-datos-agroplan` desde `dev`.

## Specs

- **S1** — Trece tablas nuevas sobre la ya existente `usuarios`: `cultivos`, `suelos`,
  `proyectos`, `terrenos`, `proyecto_cultivos`, `sistemas_riego`, `sectores`, `sector_bloques`,
  `red_tramos`, `red_nodos`, `agente_corridas`, `agente_recomendaciones`, `agente_fuentes`.
- **S2** — `caudal_disponible_m3h` vuelve, opcional y por fuente de agua. Texto exacto del
  usuario: *"volve el caudal_disponible_m3h pero con el el sistema debe funcionar bien.
  si no se lo pasa el cliente el sistema debe asignar uno y por eso el sistema podra dar todas
  las recomendaciones. pero luego puede optar a editarlo."* El valor efectivo se persiste
  siempre; el origen (`cliente`/`asumido`) queda registrado.
- **S3** — Texto exacto: *"Privado: 1 usuario = dueño de sus proyectos"*. Todo proyecto cuelga
  de `usuarios.id`; sin tabla de miembros ni roles por proyecto.
- **S4** — Texto exacto: *"Híbrido: LLM elige/justifica, motor determinístico calcula"*. El
  schema de salida del agente (`PropuestaAgente`) no admite polígonos, áreas ni cómputos.
- **S5** — Texto exacto: *"Backend genera, front solo pinta"*. La geometría se persiste como
  `jsonb` con esquema documentado; el cliente nunca envía áreas ni perímetros.
- **S6** — Texto exacto: *"Snapshot inmutable por corrida"*. Entrada, salida, modelo,
  `motor_version`, `prompt_version` y fuentes se congelan en cada corrida.
- **S7** — Texto exacto: *"Manual + re-corrida al cambiar el intake"*. `agente_corridas.intake_hash`
  permite saber si el resultado vigente quedó desactualizado sin volver a correr el agente.
- **S8** — Texto exacto: *"solo el esquema, ademas ten en cuenta algo nosotros tenemos que
  implemetar los cambios pero crea una nueva rama que parte de dev para hacer un pr"*.
- **S9** — Modelos portátiles: `alembic upgrade head` debe funcionar igual sobre SQLite (dev
  por defecto en `config.example.py`) y sobre PostgreSQL (Cloud SQL, `psycopg2`). `JSON` con
  variante `JSONB` y `Uuid` genérico, sin `ARRAY` ni `gen_random_uuid()`.
- **S10** — Convenciones del repo: español, `snake_case`, tablas en plural, `StrEnum` para
  dominios, `Mapped`/`mapped_column`, capas `routers → services → repository`, Alembic.
- **S11** — El agente correrá contra un gateway OpenAI-compatible (*"con opencode-go una api key"*)
  con web search en vivo (*"Web search en vivo como tool"*). Fuera del alcance de este PR: se
  documenta en los comentarios del modelo `AgenteCorrida`.

## Tasks

- T1 — Enums de dominio + modelos `cultivos`, `suelos`, `proyectos`, `terrenos`. S1, S2, S3, S9, S10. inline. **commit 76d2b6d**
- T2 — Modelos `proyecto_cultivos`, `sistemas_riego`, `sectores`, `sector_bloques`, `red_tramos`, `red_nodos`. S1, S5, S9. inline. **commit a4f0cb7**
- T3 — Modelos `agente_corridas`, `agente_recomendaciones`, `agente_fuentes`. S4, S6, S7, S11. inline. **commit a4f0cb7**
- T4 — Schemas Pydantic v2 de entrada/salida por recurso + contrato del agente. S2, S4, S5. inline. **commits d29a2ac, 018add4**
- T5 — Migración Alembic rev2 con las 13 tablas + catálogo `cultivos`/`suelos` sembrado. S1, S8, S9. inline. **commit d314be8**
- T6 — Verificación: `alembic upgrade head` y `downgrade base` en SQLite limpio, DDL offline para
  PostgreSQL, suite `pytest` existente. S9. inline. **evidencia en Log L8**
- T7 — Commits por unidad revisable en la rama. S8. inline. **5 commits, 76d2b6d → d314be8**
- T8 — Cerrar hallazgos de verificación (S4 wording, TerrenoUpdate, tests del esquema).
  S2, S4, S9. inline.

Slices de la rama (871 líneas en los dos primeros commits, el resto por debajo de 400):
modelos base · modelos de riego y agente · contratos de paso 1–2 · contratos de riego y agente ·
migración y semilla. El PR completo supera las 400 líneas: conviene publicarlo como PR encadenados
(esquema → contratos → migración) en lugar de uno solo.

## Log

- L1 — Pedido original, textual: *"quiero que hagamos algo, no vas a implementar nada solo vamos a
  ayudar a los que estan haciendo el backend porque estan medio volados. asi que dame por cada
  patalla los datos necesarios para enviar al backend por ejemplo del paso 1 . Quiero que me des
  que datos debe mandar el usuario los mas necesarios para funcionar el agente especializado, te
  mando la informacion necesaria @PRD-Visual-AgroPlan.md. tienes mas oreguntas?."* Flujo declarado:
  productos + área + suelo + tipo de salida de agua → el agente investiga → devuelve puntos para
  pintar la distribución diferenciada por producto → y el sistema de riego óptimo (con líneas).
- L2 — Corrección, textual: *"hay cosas que mejorar: 1. quita el caudal_disponible_m3h."* Más la
  pregunta: ¿el cliente ya no puede dibujar el polígono, o solo manda el área?
- L3 — Corrección que revierte L2, textual: *"volve el caudal_disponible_m3h pero con el el sistema
  debe funcionar bien. si no se lo pasa el cliente el sistema debe asignar uno y por eso el sistema
  podra dar todas las recomendaciones. pero luego puede optar a editarlo."*
- L4 — Respuestas al cuestionario: modelo *"con opencode-go una api key"*; conocimiento *"Web search
  en vivo como tool"*; disparo *"Manual + re-corrida al cambiar el intake"*; entrega *"solo el
  esquema, ademas ten en cuenta algo nosotros tenemos que implemetar los cambios pero crea una nueva
  rama que parte de dev para hacer un pr"*.
- L5 — Decisión del padre ante la pregunta de L2: el contorno del terreno **lo dibuja o tipea el
  cliente** (el área se deriva, nunca se recibe); los bloques de cultivo se generan por el motor y
  el cliente los ajusta; la red de riego nunca se dibuja a mano.
- L6 — Hallazgo previo al trabajo: `backend/app/core/config.py` no existe en el repositorio (solo
  `config.example.py`), por lo que el backend commiteado no importa. Se usa local y temporalmente
  para verificar; no se commitea.
- L7 — Corrección de conteo: de 12 a 13 tablas nuevas. Se agrega `sector_bloques` porque el modal
  3.1 muestra, por sector, qué cultivo y qué superficie entran; sin ese vínculo esa fila no se
  puede calcular y un bloque partido entre dos sectores no se puede representar.
- L8 — Evidencia de T6: SQLite limpio → `upgrade head` crea 15 tablas (13 nuevas + `usuarios` +
  `alembic_version`), 8 cultivos y 4 suelos; el CHECK `ck_terrenos_caudal_coherente` rechaza
  `origen=cliente` sin caudal informado; `downgrade base` deja la base vacía y vuelve a subir.
  PostgreSQL `upgrade head --sql` renderiza 15 `CREATE TABLE` con `UUID` y `JSONB` y los INSERT del
  catálogo. Suite existente: 7 tests pasan. `ruff check app alembic`: limpio salvo el N999
  preexistente de `config.example.py`.
- L9 — Verificación independiente: pasó todas las sondas. Dos hallazgos. (1) La redacción de
  S4 contradecía `CultivoRecomendado.area_m2`: el campo es correcto —el agente propone una
  asignación de superficie y la geometría la calcula el motor, cuyo polígono derivado es el
  área autoritativa—, así que se corrigió el texto con un comentario inline en el campo y no
  la estructura. (2) Faltaba el contrato de actualización parcial del caudal que S2 exige
  (*"pero luego puede optar a editarlo"*): se cerró con `TerrenoUpdate` y su regla tri-estado
  —ausente = no se toca, `null` explícito = se borra el valor del cliente y el sistema
  re-asigna desde la fuente de agua volviendo a procedencia `asumido`, número = `cliente`—
  más `limpia_caudal` para que el consumidor distinga "ausente" de "null" con
  `model_fields_set`. Se agrega `backend/tests/test_esquema_dominio.py` con 9 pruebas de
  regresión (S1, S2, S4, S5, S7, S9).
