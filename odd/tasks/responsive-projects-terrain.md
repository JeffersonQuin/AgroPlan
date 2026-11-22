# Responsive de `/projects` y `/proyectos/:proyectoId/terreno`

Hacer responsive el dashboard de proyectos y el paso 1 del wizard (terreno), con el mismo
criterio que ya se usó en `/login` y `/register`, y confirmar que los íconos de esas pantallas
siguen renderizándose con `@ng-icons` (ya migrados en `4bda26d`).
Rama `feat/responsive-projects-terrain` creada desde `origin/dev` en el worktree
`AgroPlan-responsive`, para no tocar la rama en la que trabaja el otro agente.

## Specs

**S1** — Pedido del usuario, textual: *"ahora vamos a hacer lo mismo en las otras oaginas es
decir cambiar a iconos de ng y que sea responsive ya sabes como trabajar sabiendo que el otro
agente esta trabajando @src/app/features/projects/projects.page.html y
@src/app/features/terrain/terrain.page.html"*.

**S2** — Íconos: los de estas dos pantallas usan `<ng-icon>` de `@ng-icons` y no queda ningún
`<span class="material-symbols-outlined">` en `src/`. Evidencia al abrir la tarea: el conteo de
`material-symbols-outlined` en `frontend/src` es **0** (migración hecha en `4bda26d`), así que
esta spec es una invariante a preservar, no trabajo nuevo.

**S3** — Responsive, con el criterio ya aplicado en auth: mobile-first, sin overflow horizontal
a 360 px, sin contenido cortado por `overflow-hidden`, con la acción principal alcanzable sin
scrollear de más, y escalando paddings/grillas en `sm`/`md`/`lg`. Aplica a `/projects` y a
`/proyectos/:proyectoId/terreno` incluyendo sus componentes hijos (header, toolbar, filtros,
tarjetas, modal, form, canvas y summary).

**S4** — Aislamiento: el trabajo vive en una rama nueva desde `dev` y en un worktree aparte
(`AgroPlan-responsive`), porque el otro agente trabaja en el worktree principal.

## Tasks

- **T1** — Mapa de debilidades responsive de las dos pantallas y sus hijos. Specs: S3.
  Route: explore. Hecho (evidencia en L3).
- **T2** — Responsive de `/projects` (página + header + toolbar + filtros + tarjetas + modal +
  footnote). Specs: S3. Route: writer. Hecho en `c532577`.
- **T3** — Responsive de `/proyectos/:proyectoId/terreno` (página + wizard-header + form +
  canvas + summary). Specs: S3. Route: writer. Hecho en `c4986ce`.
- **T4** — Verificación: specs existentes verdes, `ng build` verde y medición real en Chromium
  headless a 360, 768, 1024 y 1280 px. Specs: S2, S3. Route: inline. Ver `## Verification`.

## Log

**L1** — Pedido original del usuario, textual: *"perfecto ahora vamos a hacer lo mismo en las
otras oaginas es decir cambiar a iconos de ng y que sea responsive ya sabes como trabajar
sabiendo que el otro agente esta trabajando @src/app/features/projects/projects.page.html y
@src/app/features/terrain/terrain.page.html"*.

**L2** — Evidencia: `grep -rn "material-symbols-outlined" frontend/src | wc -l` → `0`. Los
íconos de ambas pantallas ya son `<ng-icon>`; `projects.page.html:47,54` y el resto de los
componentes. No hay trabajo de íconos pendiente en este alcance.

**L3** — Evidencia del mapa responsive (exploración con `path:line`):

- Los tokens de `styles.css` **no cambian por breakpoint**: `margin-desktop` = 24px a cualquier
  ancho (:88), `space-lg` = 16px (:85). Por eso `px-margin-desktop` en `projects.page.html:5` y
  en `app-header.ts:18` come 48px de un viewport de 360px.
- `/projects`: grilla correcta (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`), pero el tile de
  "nuevo plano" tiene `min-h-[380px]` (`projects.page.html:40`), el bloque de tabs de
  `projects-filters.ts:36-55` no envuelve y desborda 312px, el modal de
  `project-create-modal.ts:31` no tiene contenedor scrolleable (acciones inferiores
  inalcanzables en teléfono), y el header suma tres bloques fijos en una fila que no envuelve
  (`app-header.ts:18`, nav oculta hasta 1280px en :36).
- `/terreno`: `terrain.page.html:9` usa `overflow-hidden` sobre la grilla de tres paneles y
  `lg:grid-cols-[300px_1fr_320px]`; los raíles capan su alto con `max-h-[calc(100vh-5rem)]`
  cuando el chrome real mide 96px (`terrain-form.html:1`, `terrain-summary.html:1-2`);
  `wizard-header.html:5` tiene un `w-[290px]` fijo que comprime el nombre del proyecto a nada a
  360px; el croquis (`terrain-canvas.html:63`) tiene `min-h-[420px]` con `viewBox` fijo 740×480.
- **Restricción dura**: `terrain-canvas.spec.ts` inmoviliza el `viewBox`, el marco y la
  estructura del `<g>`; el responsive del croquis se hace por layout, no tocando la geometría.

## Verification

- `ng test --watch=false`: 24 archivos / 152 tests verdes.
- `ng build`: exit 0, `Prerendered 2 static routes.`
- Capturas reales en Chromium headless contra `ng serve` en `:4400` y un backend local con
  CORS abierto a ese origen, con sesión sembrada en `localStorage` para poder ver datos:
  `/projects` a 360, 768 y 1024; `/proyectos/:id/terreno` a 360, 768, 1024 y 1280.
  Resultado observado: sin overflow horizontal en ningún ancho, header de `/projects` en una
  fila con la CTA como ícono a 360 y con la nav visible a 1024, wizard-header en dos filas por
  debajo de `lg` y en una desde `lg`, tres paneles intactos desde `lg`, y la CTA principal
  siempre alcanzable.
- Ajuste posterior a la primera captura de 1024: el pill de autosave volvía a partirse en dos
  líneas y "Exportar PDF" hacía lo mismo; el pill pasó a mostrarse desde `xl` y los botones
  del header ganaron `whitespace-nowrap`.
- El `environment.ts` y el `public/__seed.html` usados para sembrar la sesión se revirtieron y
  borraron antes de commitear: `git status` sólo lista los archivos de la tarea.
