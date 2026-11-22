# Paso 2: cultivos contra el backend

Segundo slice de la integración: la pantalla de cultivos consume el contrato que el
backend ya expone (bloques con derivados, balance y aptitud de suelo).

## Specs

**S1** — Pedido del usuario, textual: *"perfecto ahora si esta perfecto el paso 1"* y,
al elegir el siguiente paso, *"Mergear #19 y seguir con el paso 2"*.

**S2** — Del prototipo `frontend/paso2.html`, el paso 2 muestra: cabecera con el proyecto
y la capacidad hidráulica de referencia; panel izquierdo con los parámetros del cultivo
(especie, consumo, ciclo, modo de asignación, área, siembra, cosecha, Kc pico); centro con
el croquis de bloques; panel derecho con "Cultivos Configurados" (zona, superficie,
demanda) y el balance.

**S3** — Del contrato del backend (PR #18): `GET /proyectos/{id}/cultivos` devuelve los
bloques con `porcentaje`, `demanda_total_l_dia`, `ciclo_dias`, `kc`, `dias_a_cosecha`,
`aptitud_suelo` y `advertencias`; `GET .../cultivos/balance` devuelve el panel; `POST`
acepta `cultivo_codigo` o `producto_texto`; `PATCH` y `DELETE` por bloque.

## Alcance de este turno

- Cabecera del wizard compartida por los cuatro pasos (deja de vivir en `terrain`).
- `CultivosApi`, modelos y `CultivosStore` contra la API: carga proyecto + terreno +
  bloques + balance + catálogo, alta por porcentaje, edición, borrado y refresco del
  panel.
- Tests del store con HTTP simulado.

## Tasks

- T1 — Mover el encabezado a `features/wizard/` con entradas `paso`, `nombreProyecto`,
  `estadoGuardado` y salida `guardar`; adaptar el paso 1. S2.
- T2 — Modelos y `CultivosApi` del paso 2. S3.
- T3 — `CultivosStore`: estado, selects del catálogo, alta/edición/borrado y balance. S3.
- T4 — Página y componentes del paso 2 (formulario, croquis de bloques, panel derecho). S2.
- T5 — Ruta `proyectos/:proyectoId/cultivos` y navegación desde el paso 1. S1.
- T6 — Tests de componentes y de flujo. S2, S3.

## Log

**L1** (usuario, textual): *"perfecto ahora si esta perfecto el paso 1"*.

**L2** (usuario, elección): *"Mergear #19 y seguir con el paso 2"*.

**L3** — PR #19 mergeado a `dev` (`b1c8e83`), rama borrada, 92 tests de backend verdes
sobre `dev`. Rama nueva `feat/paso2-cultivos`.

**L4** — T1-T3 entregados: encabezado compartido en `features/wizard/`, y la capa de datos
del paso 2 con 6 tests nuevos (116 en total). La UI del paso 2 queda para el turno
siguiente.

---

# Cambio de lógica del paso 2: productos → agente → reparto

**S4** — Pedido del usuario, textual: *"El usuario lo unico que tiene entrar por input es los
productos, ya sea los productos predeterminados o elegir un nuevo producto (por ejemplo: yuca).
Lo que debera hacer el sistema es donde muestra la distribucion por defecto mostrara el input
anterior osea lo que dibujo el cliente en el paso 1. Y cuando el cliente termina de agregar los
productos … habra un boton de generar y este boton lo que hara es mandar toda la informacion de
los productos al Agente y lo que hara el agente es buscar la manera mas eficiente de ordenar
todos los productos dentro de area que ingreso el cliente"*

**S5** — *"cuando el agente tenga toda esa informacion debe pintar en el area (ya predefinida)
todo las areas que contendra, si hay 4 productos entonces el area del cleinte se dividira en 4"*

**S6** — *"La fecha de la siembra por defecto es el mismo dia que lo configura … y la fecha de
cosecha lo tendra que devolver el agente"*.

**S7** — *"en el balance de area la parte de demanda total igual debe devolver el agente o el
backend de acuerdo a los datos que da el agente"* y *"en cultivos configurados si puedes aumentar
datos segun lo que devuelve el agente"*.

**S8** — Decisiones del usuario al cerrar: *"El agente reparte área, el motor dibuja"*; *"el
usuario solo podra generar una sola vez, por eso debemos poner un modal que le advierta"*; *"Se
permite fecha pasada, cosecha posterior"*; *"se puede ajustar y regenerar pero aca si se necesita
un plan premium"*.

- T7 — `POST /proyectos/{id}/agente` acepta `{productos, siembra}`; el intake sale de la lista y
  no de bloques previos. **f940b17**
- T8 — La siembra pisa la del modelo; la cosecha queda después; el reparto cubre el área entera
  (`AREA_COMPLETADA`). **f940b17**
- T9 — Fichas curadas de yuca, arroz, maní y plátano. **f940b17**
- T10 — UI del paso 2: productos, siembra, Generar con confirmación, sondeo, aplicar, croquis con
  el terreno por defecto y modal premium. **f1a4c7f**

**L5** — Smoke contra la API: papa + yuca con siembra 2026-11-22 → corrida `ok`, reparto de
2100 m² entre los dos productos, `aplicar` 200, balance `correcto` con 4410 L/d y 0 m²
disponibles.

**L6** — El reparto geométrico lo hace el motor: el agente sólo decide **cuánta área** va a cada
producto. Respeta el invariante del contrato (la IA nunca devuelve coordenadas).

**L7** — Las fichas nuevas (yuca, arroz, maní, plátano) son valores de arranque con criterio
agronómico general; se ajustan editando el JSON.

**L8** — Sin `AGENTE_API_KEY` un producto sin ficha curada responde 422 con el motivo real ("no
hay ficha curada y la búsqueda web no está disponible"): el sistema no inventa datos agronómicos.
Por eso los productos que el usuario va a escribir a mano necesitan ficha.

**L9** — Prueba con el modelo real (clave del usuario). Bloqueantes encontrados y corregidos:

- `agno` no estaba instalado: se declaró `agno[openai]>=3.2,<4` (pyproject + lock). Sin el
  extra `openai` el modelo OpenAI-compatible no arranca.
- El gateway de OpenCode exige la cabecera `x-opencode-session`; sin ella responde 400
  "cannot be routed efficiently". Ahora viaja el id de la corrida.
- `AGENTE_RAZONAMIENTO="low"` se pasa a `OpenAILike(reasoning_effort=...)`.

Resultados medidos con `deepseek-v4.1-flash`:

| Prueba | Tokens | Tiempo |
|---|---|---|
| Llamada directa (`ejecutar`) | 2.195 / 2.196 | 15,8 s |
| Pipeline completo por API | 2.500 / 4.053 | 30,8 s |

Reparto real: papa 1260 m² + lechuga 840 m² = 2100 exacto (el modelo eligió 60/40, no
50/50); siembra 2026-11-22 con cosecha 2027-03-22 y 2027-01-26; aplicar 200; balance
`correcto` con 3780 L/d.

**L10** — La suite forzaba la clave real: 6 tests llamaban al modelo (8 minutos, resultados
no deterministas). `conftest.py` fija `AGENTE_API_KEY=""`, así los tests van a modo catálogo.

**L11** — `AGENTE_MODO` (`catalogo` | `llm`, por defecto `catalogo`): el reparto se resuelve
por catálogo (determinístico, gratis) o con el modelo, sin tocar la clave. La investigación de
un producto fuera del catálogo **no** depende del modo: ocurre igual en los dos, porque sin ella
el producto no se puede usar. Catálogo no busca para repartir; si el producto falta, busca.

---

# El paso 2 sólo recoge datos; el agente corre una vez, al final

**S9** — Pedido del usuario, textual: *"ya que no queremos que en cada paso hagamos una peticion
a la api. … lo unico que hara los pasos es pedir informacion, porque en el paso 4 sera el resumen
es decir el informe final que entregara el agente (distribucion de todo en el area, el sistema de
riego adecaudo, etc). asi que este paso lo unico que debe pedir es productos, fecha de siembra y
cultivos configurados si no tienes informacion que diga que espere hasta el final en el resumen
para ver todo a detalle. … asi no gastamos muchos tokens solo un prompt final para el agente"*

- T11 — `WizardDraftStore`: borrador de los pasos (productos + siembra), en memoria y
  `localStorage` por proyecto, con el payload listo para el disparo del paso 4. **f928bd4**
- T12 — El paso 2 queda de recolección: nada de generar, sondear ni aplicar. El panel dice que
  el detalle llega en el resumen final. **f928bd4**
- T13 — Se quita el sondeo, los modales de generación y las escrituras del paso 2; la API del
  agente queda para el paso 4. **f928bd4**

**L12** — Consecuencia: el costo del agente queda en **un solo prompt por proyecto**, al generar
el resumen. Los pasos 1-3 sólo hacen lecturas (`GET`), que no cuestan tokens.

**L13** — Pendiente para el paso 4: disparar con `WizardDraftStore.aPayload()`, sondear, aplicar y
renderizar el informe (distribución, demanda, cosechas, sistema de riego, fuentes).
