# Paso 1 funcional: proyectos → terreno contra el backend

Primer slice de la integración con el frontend: el botón "Nuevo proyecto" crea el
proyecto en la API y entra al paso 1, y el paso 1 guarda el terreno en el backend, que
pasa a ser la fuente de verdad de las medidas.

## Specs

**S1** — Pedido del usuario, textual: *"pondremos funcionalidad a la parte de
frontend/src/app/features/projects/projects.page.html que es punto de empiezo para un
proyecto, pero en esta parte solo pondremos funcionalidad a los botones de "Nuevo
proyecto". donde ese boton entrara al primer paso que es
frontend/src/app/features/terrain/terrain.page.html, asi que completaremos esta slice
primero que todo este bien y vamos por el paso 2 pero primero el paso 1"*

**S2** — El backend ya expone el contrato (rama `dev`, PR #18): `POST /proyectos`,
`GET /proyectos`, `GET /proyectos/{id}`, `PUT /proyectos/{id}/terreno`,
`GET /proyectos/{id}/terreno`, `GET /catalogos/suelos`. El front no calcula medidas que
el backend ya deriva.

**S3** — Del contrato del flujo: el paso 1 es el polígono, el suelo y el agua; el área, el
perímetro y los lados los deriva el backend desde los vértices.

## Alcance

- Botones "Nuevo proyecto" (header, toolbar y tarjeta fantasma) abren el modal.
- El modal crea el proyecto en la API y navega a `proyectos/{id}/terreno`.
- El dashboard lista los proyectos reales del usuario.
- El paso 1 carga proyecto y terreno, guarda con `PUT /terreno` y muestra los derivados
  del backend (área, perímetro, lados, caudal efectivo y su procedencia, alertas).
- "Continuar a Cultivos" guarda el terreno. El paso 2 es el slice siguiente: el botón no
  navega todavía.

## Fuera de alcance

- Paso 2, riego, agente desde la UI.
- Edición de proyectos y borrado desde la grilla.
- Croquis editable en el canvas (el canvas sigue siendo la referencia visual).

## Tasks

- T1 — Modelos y `ProjectsApi` (contrato HTTP + mapeo al modelo de la tarjeta). S1, S2.
- T2 — `ProjectsStore` contra la API: cargar, crear, errores y estados. S1.
- T3 — Modal async + navegación al paso 1, y el dashboard con datos reales. S1.
- T4 — `TerrainApi`, `toVertices` y `TerrainStore` con carga y guardado. S2, S3.
- T5 — Formulario y resumen con los derivados del backend; botón continuar. S3.
- T6 — Ruta `proyectos/:proyectoId/terreno` y `TerrainPage` con el id del proyecto. S1.
- T7 — Tests de api, stores y componentes. S1-S3.
- T8 — Build y tests del proyecto con el Node del CLI.

## Log

**L1** (usuario, textual): *"ahora primero haremos lo siguiente pondremos funcionalidad a la
parte de frontend/src/app/features/projects/projects.page.html que es punto de empiezo para un
proyecto, pero en esta parte solo pondremos funcionalidad a los botones de "Nuevo proyecto".
donde ese boton entrara al primer paso que es
frontend/src/app/features/terrain/terrain.page.html, asi que completaremos esta slice primero
que todo este bien y vamos por el paso 2 pero primero el paso 1"*

**L2** — Implementado en `feat/paso1-frontend` (PR #19, sin mergear): `ProjectsApi` y
`ProjectsStore` contra la API, modal que crea y navega con el id real, `TerrainApi` con
`PUT`/`PATCH`, `TerrainStore` que carga proyecto + terreno + suelos y guarda las cotas como
vértices, resumen y encabezado con los derivados del backend, y la ruta
`proyectos/:proyectoId/terreno`.

**L3** — 86 tests del frontend verdes y build de desarrollo OK. Los tests corren con el Node 24
de `npx` porque el CLI de Angular 22 rechaza el Node 22.22.2 del sistema.

**L4** — Contrato cruzado verificado contra uvicorn: el payload exacto del front
(`toVertices(60, 30, 40, 20)`, 5 vértices, trapecio) da `PUT` 200 con área 2100,0 m² y
perímetro 186,06 m; el cálculo local del front da 2100 m². Coinciden. `GET /proyectos` refleja
el área en la grilla.

**L5** — Decisiones para el próximo slice: (a) el mockup muestra 3.200 m² mientras sus cotas
dan 2.100 — se mantiene el número del diseño en la primera pintura y el real al guardar;
(b) la figura del prototipo tiene 5 vértices (cierra con diagonal), así que el backend informa
"5 lados" y no "4 lados (trapecio)".

**L6** — El usuario eligió *"la forma manda: cada una pide sus cotas"*. Canvas y geometría
quedaron así:

- `toVertices(dimensions, shape)`: rectángulo = 4 vértices desde largo × alto; trapecio y libre
  = la figura de 5 puntos del prototipo. `calculateMetrics` y `fromVertices` son coherentes con
  las tres formas.
- El canvas proyecta esos mismos vértices al marco del diseño (130..610 × 70..420, escala
  uniforme) y rotula cada lado con su longitud; el contorno de servicio sigue la figura.
- El formulario esconde base inferior y lateral derecho cuando la forma es rectángulo.
- Se retiró `REFERENCE_METRICS`: el resumen mostraba 3.200 m² mientras las cotas dan 2.100 y
  el dibujo real los contradecía. Ahora los números salen siempre de la geometría.
- Los botones de zoom, paneo, cuadrícula y vértices quedan deshabilitados con su motivo.

Contrato cruzado verificado contra uvicorn: rectángulo 60 × 40 → backend
`area_m2 2400`, `perimetro_m 200`, `lados 4`, `lados_m [60, 40, 60, 40]`; el front calcula
2400 m² y 200 m. Coinciden. 96 tests verdes.
