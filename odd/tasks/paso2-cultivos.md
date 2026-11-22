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
