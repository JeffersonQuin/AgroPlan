# Paso 3 — Sistema de riego (sólo restricciones)

Paso 3 del wizard de AgroPlan: recoge **restricciones** del usuario (energía disponible, si ya
tiene tanque, presupuesto) y no calcula ni decide nada. Todo lo que el agente produce vive en el paso 4.

Branch: `feat/paso3-riego` (base `dev`). Feature: `frontend/src/app/features/riego/`.

## Specs

- **S1** El paso 3 sólo recoge datos: no escribe en la API, no llama al agente y no muestra
  números calculados. Distribución de área, sistema de riego, trazo, sectores, turnos, presión y
  cómputo de materiales son salida del agente y aparecen recién en el paso 4.
- **S2** Los inputs del paso 3 son tres: energía disponible (`Red eléctrica` | `Solar`, por
  defecto `Red eléctrica`), si ya tiene tanque (`No tiene` | `2.500 L` | `5.000 L` | `10.000 L`,
  por defecto `No tiene`) y presupuesto en Bs, opcional.
- **S3** El presupuesto es opcional y cuando se informa el paso 3 explica su uso:
  "Si ponés un presupuesto, el agente elige los materiales dentro de ese presupuesto."
- **S4** El presupuesto tiene un piso de **100 Bs** (sirve también para un jardín chico de patio).
  Un monto mayor a 0 y menor a 100 no se manda al agente (`presupuesto_bs: null`) y el paso 3 lo
  avisa: "El mínimo para un sistema de riego es 100 Bs; ese monto no se manda al agente."
  Vacío es `null` y no genera aviso.
- **S5** El paso 3 muestra la fuente de agua y el caudal disponible que ya cargó el paso 1 —no los
  vuelve a pedir— y avisa cuando el terreno no tiene caudal informado.
- **S6** El borrador guarda las tres restricciones en el mismo `localStorage` del wizard, por
  proyecto, y `aPayload()` las envía como `restricciones: { energia, tanque_l, presupuesto_bs }`.
  Un borrador guardado antes de este paso (sin `restricciones`) carga con los valores por defecto.
- **S7** Navegación: ruta `proyectos/:proyectoId/riego` (título `Sistema de riego · AgroPlan`,
  `authGuard`); el botón "A Sistema" del paso 2 navega ahí; "Continuar a Resultado" queda
  deshabilitado con el título "Paso 4 (Resultado): próximamente".

## Tasks

- [x] **T1** Restricciones en el borrador: modelo `restricciones.model.ts` + `WizardDraftStore` (energía, tanque, presupuesto con piso) + spec del borrador — S2, S3, S4, S6 — commit `b463728`
- [x] **T2** Feature `riego`: `riego.model.ts`, `riego.api.ts`, `RiegoStore` de sólo lectura, `RiegoPage`, `RiegoForm`, ruta y spec de página — S1, S2, S3, S5, S7 (ruta) — commit `86bf626`
- [x] **T3** Navegación paso 2 → 3: "A Sistema" navega a `/proyectos/:id/riego` y "Continuar a Resultado" queda deshabilitado — S7 — commit `84229d7`

Cortes de revisión: cada commit es un corte (`b463728` borrador, `86bf626` pantalla, `84229d7`
entrega del paso 2).

## Evidencia

- `ng test --watch=false` (Angular 22 vía `npx -y -p node@24 node ./node_modules/@angular/cli/bin/ng.js test`): **22 archivos, 135 tests verdes**, incluidos los 5 de `riego.page.spec.ts` y los 6 nuevos de `wizard-draft.store.spec.ts`.
- El spec de la página verifica lo que el paso **no** hace: `http.expectNone('.../agente')` y `http.verify()` en `afterEach` (ninguna escritura).
- Specs nombrados por regla: fuente y caudal del paso 1 (S5), restricciones y payload (S2, S6), aviso por debajo del piso (S4), copia del presupuesto opcional (S3), aviso sin caudal (S5), enlace del paso 2 (S7).

## Log

- **L1** (usuario) "El paso 3 pero no haremos todo porque desde el paso 2 decidimos que el paso 4
  sera el que genere todo lo que el agente debe generar como ser la distribucion adecuada, y demas
  el sistema de riego mas adeacuado y el trazo ,etc"
- **L2** (usuario) "vamos con la opcion de "solo restricciones" pero incluyendo que el input de
  presupuesto puede ser opcional pero que haya un mensaje que diga que si pone el presupuesto el
  agente puede usar ese presupuesto para usar materiales dentro de ese presupuesto, pero teniendo
  en cuenta no como mandal al agente ejemplo manda 1 bs y ahi como que no eso ya es burla ubicas?"
- **L3** (usuario) "No: el balance va al paso 4"
- **L4** (usuario) "puede ser minimo 100 0 200 porque como te dije puede usar un usuario normal que
  tiene un pequeño jardin en su patio y quiere hacer algo pequeño" → piso 100 Bs.
- **L5** (usuario) "Red eléctrica y solar"
- **L6** (evidencia) `frontend/paso3.html` tiene sólo dos selects reales (tanque y bomba); el trazo
  SVG, sectores, emisores, diámetros, turnos, presión y cómputo están hardcodeados. El backend ya
  tiene el contrato de riego (`sistemas_riego`, `sectores`, `red_tramos`, `red_nodos`,
  `GET/PUT /proyectos/{id}/riego`, `GET .../riego/preview`), pero el paso 3 no lo usa: no escribe
  y no calcula (S1, L3).
- **L7** (evidencia) `WizardDraftStore` guarda en la clave global `agroplan.borrador` y valida
  `proyectoId` al leer; la extensión de S6 mantiene esa forma y agrega `restricciones`.
- **L8** (decisión) La bomba y el modelo de tanque del prototipo **no** son inputs: el agente elige
  el equipo en el paso 4. El tanque del paso 3 es sólo "ya tiene / no tiene y de cuántos litros".

- **L9** (verificación independiente) Todos los ítems S1–S7 en `pass`. Hallazgo real: `normalizarMonto` redondeaba, así que un presupuesto de 99,6 Bs pasaba el piso de 100 al enviarse. Corregido a truncado (`Math.floor`) y cubierto con un test propio en `wizard-draft.store.spec.ts`.
