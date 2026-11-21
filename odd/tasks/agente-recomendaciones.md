# Agente de recomendaciones AgroPlan — pipeline embebido en el FastAPI

Rehacer el agente (commit `dad0fb6`) dentro de `backend/app/agente/` para que cierre el
circuito de corridas acordado: el servicio persiste, el humano aplica, la IA no escribe.
Riesgo alto: cambia el contrato de la API que consume el front (item 3).

## Specs

**S1** — Pedido del usuario, textual: *"si quiero que resuelvas las observaciones y rehacerlo
con la arquitectura, quiero que funcione tal y como lo planeamos con en
Plan_Integral_AgroPlan_Diseno_Instalaciones.pdf"*

**S2** — Plan integral, textual: *"El asistente IA consulta resultados ya calculados y los
explica; no modifica silenciosamente la geometría."* Y en "No delegar a la IA": *"Cálculo de
longitudes, áreas, cantidades, caudales o pérdidas sin motor verificable. Inventar normas,
diámetros permitidos, pendientes o especificaciones. Aprobar un diseño como seguro o
reglamentario. Modificar nodos o tuberías sin confirmación del usuario."* Y: *"Lenguaje natural
a acciones: LLM con JSON estructurado + validación «Agrega una derivación de 2 m al este con
válvula»; backend valida antes de aplicar."*

**S3** — `docs/flujo-sistema-agroplan.md`, textual: *"El agente tarda entre 5 y 30 segundos. No
se bloquea el request"*; *"Estados: `pendiente` → `corriendo` → `ok` | `error`"*; *"Si el
cliente vuelve a apretar **Analizar** con el mismo intake, se responde la corrida vigente
(`intake_hash` igual) en lugar de gastar otra llamada"*; *"dos corridas simultáneas → 409"*;
*"Solo después de aplicar existen bloques que el cliente pueda editar en el paso 4"*;
*"Índices 1-based sobre las fuentes recuperadas en la corrida, no ids inventados por el
modelo"*; correcciones del backend: `CULTIVO_FUERA_DE_CATALOGO`, `AREA_AJUSTADA`,
`DEMANDA_AJUSTADA`, `FECHAS_AJUSTADAS`, `FUENTES_INCOMPLETAS`; y `POST
/agente/corridas/{corrida_id}/aplicar` → 200 · 409.

**S4** — Observaciones a resolver, todas obligatorias:
1. La corrida se crea y se cierra por la API (`salida`, `modelo`, versiones, tokens,
   `duracion_ms`, `error_detalle`, `estado`), no por stdout.
2. El agente no escribe el proyecto: `aplicar` es el único paso que crea bloques y riego.
3. `intake_hash` sale del intake del backend, nunca de la salida del LLM.
4. `agno` queda declarado/aislado; sin credenciales el pipeline funciona en modo catálogo.
5. Las fuentes y `fuente_ids` son reales, persistidas en `agente_fuentes`.
6. Los contratos son los de `app.schemas.agente`, sin espejos duplicados.
7. Las correcciones del servicio se aplican antes de congelar la salida.
8. El reparto por porcentaje nunca excede el terreno; no quedan escrituras parciales.
9. Sin `backend/Agno_agent/main.py` ni cambios de front en el mismo commit.

## Tasks

- T1 — Config `AGENTE_*` en `app/core/config.example.py` y `app/core/config.py`. S3. inline.
- T2 — `app/agente/` (instrucciones, cliente Agno + modo catálogo, validación/correcciones)
  sobre los schemas reales. S2, S4-4, S4-6, S4-7. inline.
- T3 — `services/agente.py`: `ejecutar_corrida` con transiciones de estado, snapshot y
  idempotencia por `intake_hash`. S3, S4-1, S4-3, S4-5. inline.
- T4 — `aplicar_corrida` + endpoint `POST .../agente/corridas/{corrida_id}/aplicar`.
  S2, S3, S4-2, S4-8. inline.
- T5 — Router: 202 + `BackgroundTasks`, alias `GET /agente/corridas/{corrida_id}`. S3. inline.
- T6 — Eliminar `backend/Agno_agent/main.py`. S4-9. inline.
- T7 — Tests de contrato y de flujo en `tests/test_agente_api.py`; ajustar
  `tests/test_proyectos_api.py`. S2, S3, S4. inline.
- T8 — Verificación independiente del contrato. inline + verifier.

## Log

**L1** (usuario, textual): *"ya mandaron el agente los del backend quiero que verifiques si esta
bien implementado. segun a lo quedamos (revisa tus memorias), ademas hicieron varios endpoints y
demas"*

**L2** (usuario, textual): *"si quiero que resuelvas las observaciones y rehacerlo con la
arquitectura, quiero que funcione tal y como lo planeamos con en
Plan_Integral_AgroPlan_Diseno_Instalaciones.pdf"*

**L3** — Evidencia de la revisión: el commit `dad0fb6` solo trae `backend/Agno_agent/main.py`
(más ruido de front); los endpoints del agente ya existían del commit del esquema; `agno` no
está en `pyproject.toml` ni en `.venv`; `_intake_hash` se calculaba desde la propuesta del LLM;
`fuente_ids` hardcodeado en `[1, 2]`; el script escribía bloques y riego sin `aplicar`.

**L4** — Implementación entregada en `feat/agente-recomendaciones`: `e7e7ce4` (módulo del
agente + config + retiro del script standalone), `dea209e` (ciclo de corridas y `aplicar`),
`a704b59` (14 tests nuevos + ajuste de los 2 existentes). Suite: 35 tests verdes; ruff sin
hallazgos nuevos. El script `backend/Agno_agent/main.py` se elimina y queda un README con el
flujo.

**L5** — Límites conocidos: la ruta contra el LLM real no tiene prueba de ejecución porque
`agno` no está instalado en el venv ni declarado en `pyproject.toml` (modificar el lock sin
red es riesgoso). El pipeline queda cubierto de punta a punta en modo catálogo.

**L6** — Smoke test contra uvicorn real (SQLite temporal, migración + seed por servicio, JWT
real): `POST /proyectos/{id}/agente` → 202 → `estado: ok` en el primer poll, con
`modelo: catalogo`, 2 cultivos (los pedidos), 2 fuentes persistidas y `fuente_ids` 1-based;
`aplicar` → 200 con bloques 120/80 exactos, 1 sector y 42 tramos; `POST /agente` después de
aplicar → 200 con la **misma** corrida; `aplicar` de nuevo → 409; sin token → 401.

**L7** — Ese smoke destapó dos defectos ya corregidos en `5fc2b2f`: el fallback rellenaba
hasta 8 cultivos (inventaba) y `aplicar` derivaba un área distinta de la congelada por el
redondeo del porcentaje, lo que cambiaba el intake y gastaba una corrida nueva. Ahora las
áreas se cuantizan a la grilla de 0,01% del terreno y hay dos tests de regresión.

**L8** — Límite de revisión: los commits de esta feature suman ~1.100 líneas de código de
autoría nueva en 4 commits; el commit `e7e7ce4` incluye el retiro del script standalone
porque estaba en el índice. Para publicar conviene PR encadenado: 1) módulo del agente +
config, 2) ciclo de corridas + aplicar, 3) tests.

**L9** — Verificación independiente (`gentle-ai-verify`, 17 sondas propias + suite). Veredicto:
S1, S2, S4-1..S4-9 PASS; S3 parcial por **un** desvío real: faltaba
`POST /agente/corridas/{corrida_id}/aplicar`, la ruta que documenta el contrato (404). Además
dos hallazgos: `tanque_l` sin clamps reventaba el payload de riego después de borrar bloques
(500 con escritura parcial) y `repartir_porcentajes` sin guarda ante suma > terreno. Corregido
en `576ba1e`, adoptando su batería de 13 tests con `get_db` real de producción.

**L10** — Estado final: 49 tests verdes, ruff limpio (salvo N999 preexistente), smoke contra
uvicorn real con la ruta del contrato (`200` y `409` en la scoped). Único hueco de prueba: la
ruta LLM real, porque `agno` no está instalado ni declarado.

---

# Ampliación: investigación de productos fuera del catálogo

**S5** — Pedido del usuario, textual: *"entonces el agente hace busquedas en internet
verdad?. Por ejemplo yo ingreso un producto que no esta predefinido en la base de datos, el
agente deberia scrapear internet para buscar la informacion correcta y de ahi sacar todo el
analisis con docmuentacion. cumple?"*

**S6** — Decisión del usuario sobre el producto nuevo, textual: *"Alta automática con aviso"* —
*"El agente crea el cultivo en el catálogo con la ficha y sus fuentes y lo usa en el momento,
dejando una advertencia bloqueante para revisión posterior."*

**S7** — Decisión del usuario sobre la fuente, textual: *"Híbrido: ficha curada, web de
respaldo"* — *"Primero consulta fichas curadas que cargamos nosotros (rápido, verificable, sin
red); si no hay ficha, busca en web con presupuesto de 6 y cita URL + fragmento."*

**S8** — Del plan integral (sigue vigente): *"No delegar a la IA: … Inventar normas, diámetros
permitidos, pendientes o especificaciones."* Lo investigado sólo puede alimentar la ficha
agronómica del cultivo (demanda, ciclo, meses de siembra); caudal, separaciones, bomba y
sectores siguen saliendo del motor determinístico y de los CHECK de la base.

**S9** — Del contrato del flujo: *"`AGENTE_MAX_BUSQUEDAS` | `6` | presupuesto de búsquedas web
por corrida"*; *"Búsqueda web caída | la corrida continúa, `FUENTES_INCOMPLETAS`"*;
`agente_fuentes.tipo ∈ {web, catalogo_interno, norma, manual}`.

- T12 — `cultivos.origen` y `cultivos.revisado_en` + migración (marca qué fichas creó el
  agente). S6. inline. **commit**
- T13 — `app/agente/fichas/` curadas + `app/agente/fichas.py` (búsqueda por nombre/código).
  S7. worker.
- T14 — `app/agente/investigacion.py`: híbrido con presupuesto, adaptador web inyectable,
  saneo de dominios y `ProductoNoReconocido` cuando no hay dato verificable. S7, S8, S9.
  worker.
- T15 — Alta automática: `POST /proyectos/{id}/cultivos` acepta `producto_texto`; si no está
  en el catálogo investiga, crea el cultivo con `origen='agente'` y devuelve la advertencia
  bloqueante con sus fuentes. S6. inline.
- T16 — Advertencia `PRODUCTO_NO_RECONOCIDO`: hoy un producto que no matchea se reemplaza en
  silencio. S5. inline.
- T17 — Tests de investigación, alta automática y no-inventar. inline.
- T18 — Verificación independiente. inline + verifier.

**L11** (usuario, textual): *"entonces el agente hace busquedas en internet verdad?. Por
ejemplo yo ingreso un producto que no esta predefinido en la base de datos, el agente deberia
scrapear internet para buscar la informacion correcta y de ahi sacar todo el analisis con
docmuentacion. cumple?"* — Respuesta honesta: no lo hacía; faltaba `AGENTE_MAX_BUSQUEDAS`, no
había herramienta de búsqueda y el alta de bloque rechazaba el producto con 422 antes del
agente.

**L12** (usuario, textual): *"Alta automática con aviso"* y *"Híbrido: ficha curada, web de
respaldo"*.

**L13** — Entregado en `8bbbde2` (migración `c4e9a1b73f21` + modelo + `CultivoOut`),
`2403c9e` (fichas curadas + investigación híbrida, delegado a worker) y `d2a4ade` (alta
automática en el paso 2 + `PRODUCTO_NO_RECONOCIDO`). Suite: 73 tests verdes; ruff sin
hallazgos nuevos. Contrato documentado en `docs/flujo-sistema-agroplan.md` §21.

**L14** — Decisión de implementación: una ficha **curada del repo** entra al catálogo como
`origen='humano'` y `revisado_en` con fecha (ya la verificó una persona), con aviso no
bloqueante; solo lo investigado en web queda `origen='agente'`, sin revisar y con aviso
bloqueante. Marcar como pendiente algo que ya curamos sería mentirle al revisor.

**L15** — La verificación independiente de esta ampliación se colgó (timeout del subagente a
los 45 turnos) y se canceló; la hice en la sesión principal con sondas acotadas. Resultado:
migración up/down/up y no-op sobre base migrada (8 filas, todas `humano`); `AGENTE_MAX_BUSQUEDAS`
en config y en uso (`investigacion.py:449`); diff de `BloqueCultivoCreate` contra `576ba1e`
puramente aditivo y mensaje 422 histórico idéntico; smoke contra uvicorn con
`producto_texto=quinoa` → 201 con `CULTIVO_DESDE_FICHA`, ficha en el catálogo con
`origen=humano`, `revisado_en` y fuente; producto no verificable → 422 con el motivo real y
**sin filas huérfanas**; `papa` + agente → `ok`, `aplicar` 200 y reintento 200 con la misma
corrida.

**L16** — Defecto encontrado por esas sondas y corregido: `Cultivo.nombre` es `String(60)` y
el nombre investigado entraba sin recortar (SQLite no valida largos, PostgreSQL sí). Ahora se
recorta en el saneo y otra vez en la escritura.

**L17** — Verificación independiente de la migración (relanzada con alcance reducido, 4 puntos,
sin colgarse): **PASS** en up/down/up (8 filas, todas `humano`, no-op sobre base migrada,
CHECK efectivo), **PASS** en compatibilidad PostgreSQL (SQL offline con `dialect_name`; el
`batch_alter_table` no recrea la tabla en PG porque soporta `ADD CONSTRAINT`, y en SQLite
preserva filas, FKs y los otros CHECK), **PASS** en acuerdo modelo/migración (0 diferencias en
`compare_metadata`). Sin PostgreSQL real ni `psycopg` en el venv: el DDL de PG está verificado
en modo offline, no contra un servidor.

**L18** — Avisos atendidos en el commit siguiente: el downgrade borra la trazabilidad (las
fichas del agente vuelven como `humano`) queda advertido en la migración y en §21.6; y el
modelo ahora declara también `server_default` para `origen`, así que `create_all` y la base
migrada son idénticas. Se adoptaron las 5 sondas de migración del verificador.

**L19** — Estado: 80 tests verdes, ruff limpio salvo el N999 preexistente.

---

# Slice: paso 1 y paso 2 alimentados por el backend

**S10** — Pedido del usuario, textual: *"siguiendo el flujo el cliente ingresa el poligono debe
ir con el scrren de frontend/paso1.html que es un prototipo debe llenar todo lo ncesario. y el
tipo de suelo (opciones predefinidas), y los productos, el agente reconoce los productos busca
toda la informacion del producto que sea necesaria para el funcionamiento del sistema
(incluyendo el suelo del producto matcheando y verificando si el suelo es bueno o no). cuando
llegue a esta parte de ingresar proudctos debe mostrar como en paso frontend/paso2.html toda
esa informacion debe dar el backend o el agente."*

**S11** — Decisión del usuario sobre el veredicto de suelo, textual: *"Avisar con veredicto,
nunca bloquear"* — *"La tarjeta muestra el veredicto con motivo pero el usuario puede seguir.
El suelo nunca frena la demo."*

- T19 — `cultivos.kc` + `cultivos.aptitud_suelo` + `terrenos.profundidad_nivel_dinamico_m`,
  migración `d7a1e4c9b2f0`. S10.
- T20 — Fichas e investigación traen kc, densidad, profundidad de raíz y aptitud por suelo,
  saneados por dominio. S10.
- T21 — Derivados en el bloque: porcentaje, demanda_total_l_dia, ciclo_dias, kc,
  dias_a_cosecha, aptitud_suelo, advertencias. S10.
- T22 — Veredicto de suelo como advertencia no bloqueante (`SUELO_NO_APTO`,
  `SUELO_CONDICIONADO`) con motivo y fuente. S11.
- T23 — 8 tests. **commits 3dc0c66, 7ad8a54**.

**L20** — Brecha relevada contra los dos prototipos antes de implementar: paso 1 no tenía
nivel dinámico; paso 2 no tenía Kc, ni derivados por bloque (%, L/d, días a cosecha), ni
aptitud de suelo. Lo demás ya lo daba el backend (`BalanceArea` para el panel, suelos
sembrados exactos a las 4 opciones del prototipo).

**L21** — Smoke contra uvicorn real: paso 1 → 200 m², franco, nivel 12,5, caudal 3,0 asumido;
paso 2 con `producto_texto="Zapallo"` → 140 m² (70%), 4,5 L/m²/día, 630 L/d, ciclo 130,
**Kc 1,05**, aptitud `apto` con motivo y fuente; cambiar el suelo a arcilloso → veredicto
`condicionado` con su motivo y aviso no bloqueante. Panel: 200/140/60, `ajustado`.
