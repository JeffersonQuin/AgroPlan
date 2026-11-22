# Responsive de `/proyectos/:proyectoId/cultivos` y `/riego`

Hacer responsive el paso 2 (cultivos) y el paso 3 (riego) del wizard, con el mismo criterio que
`/projects` y `/terreno`, y corregir la nota desactualizada de la spec de auth sobre el patrón de
íconos de `register-hero`.
Rama `feat/responsive-cultivos-riego` creada desde `origin/dev` en el worktree
`AgroPlan-responsive2`.

## Specs

**S1** — Pedido del usuario, textual: *"arreglalo en la proxima rama nos toca ahora las
siguientes paginas que son @src/app/features/cultivos/cultivos.page.html y
@src/app/features/riego/riego.page.html"*.

**S2** — Pedido del usuario, textual: *"arreglalo en la proxima rama"*, respondiendo a la deuda
anotada: en `odd/tasks/auth-email-password-iconos-responsive.md` el Log L17 y la nota de S3
describen el patrón de claves semánticas de `register-hero` como "alternativa aceptada", pero
`133ce64` unificó ese componente a la convención general (`FEATURE_ICONS` devuelve el nombre del
registro). La spec tiene que decir lo que el código hace.

**S3** — Responsive, con el criterio ya aplicado en `/projects` y `/terreno`: mobile-first, sin
overflow horizontal a 360 px, sin contenido cortado por `overflow-hidden`, con la acción
principal alcanzable, y escalando paddings/grillas en `sm`/`md`/`lg`. Aplica a las dos páginas y
a sus componentes hijos. Los íconos ya son `<ng-icon>` (invariante, no trabajo nuevo); el
`wizard-header` compartido ya quedó responsive en `c4986ce`.

**S4** — Aislamiento: rama nueva desde `dev` en un worktree aparte, porque el otro agente
trabaja en el worktree principal.

## Tasks

- **T1** — Mapa de debilidades responsive de las dos páginas y sus hijos. Specs: S3.
  Route: explore. Hecho (evidencia en L3).
- **T2** — Responsive de `/cultivos` (página + panel + formulario). Specs: S3. Route: writer.
  Hecho en `aea4dac`.
- **T3** — Responsive de `/riego` (página + formulario). Specs: S3. Route: writer.
  Hecho en `2744551`.
- **T4** — Corregir la nota desactualizada de la spec de auth. Specs: S2. Route: inline.
  Hecho (S3 sin el patrón alternativo + `L18`).
- **T5** — Verificación: specs verdes, `ng build` verde y capturas reales a 360/768/1024 con
  sesión sembrada. Specs: S1, S3. Route: inline. Ver `## Verification`.

## Log

**L1** — Pedido original del usuario, textual: *"arreglalo en la proxima rama nos toca ahora las
siguientes paginas que son @src/app/features/cultivos/cultivos.page.html y
@src/app/features/riego/riego.page.html"*.

**L2** — Deuda aceptada por el usuario en esa misma frase: la nota desactualizada de
`odd/tasks/auth-email-password-iconos-responsive.md` (L17 y la nota de S3 sobre el patrón de
`register-hero`). Cerrada: S3 ya no describe un patrón alternativo y se agregó `L18` ahí.

**L3** — Evidencia del mapa responsive (exploración con `path:line`):

- Las dos páginas comparten `<main>` casi idéntico (`cultivos.page.html:9`, `riego.page.html:9`):
  `p-4`, `overflow-hidden` y `lg:grid-cols-[300px_1fr_320px]`, igual que el paso 1 antes de
  `c4986ce`. Entre 768 y 1023 quedan en una sola columna con reglas internas de escritorio.
- Los raíles de las tres pantallas capan su alto con `max-h-[calc(100vh-9rem)]`
  (`cultivo-form.html:1`, `cultivos-panel.html:1`, `riego-form.html:1`), que asume un header de
  una fila de 64px; el `wizard-header` envuelve en dos filas debajo de `lg`, y los scrollbars
  están ocultos globalmente (`styles.css:149`), así que el contenido queda escondido sin señal.
- Filas `justify-between` sin wrap con un bloque `shrink-0`: cabecera de proyecto
  (`cultivos.page.html:16,24`; `riego.page.html:16,24`) y nav del wizard
  (`cultivos.page.html:111`, `riego.page.html:121`), que desbordan los 328px útiles a 360px.
- Alturas fijas: `min-h-[460px]` en la columna central de ambas (`:13`), `min-h-[360px]` y `p-8`
  en el estado vacío de cultivos (`:36`).
- Inputs `flex-1` sin `min-w-0` (`cultivo-form.html:17,48`, `riego-form.html:98`) resisten el
  shrink por min-content y empujan los botones/sufijos fuera del borde a 360px.
- Asimetría en riego: el `<aside>` derecho (`riego.page.html:168`) no tiene tope de alto mientras
  el formulario sí.
- **Acoplamientos frágiles en los specs**: `cultivos.page.spec.ts` cuenta `article`, busca un
  botón por el texto exacto `'Agregar'` y un enlace por `'A Sistema'` (orden del DOM);
  `riego.page.spec.ts` exige que `button[data-energia]` contenga un `<ng-icon>` con `<svg>`.
- No hay SVG ni canvas en estas dos pantallas.

## Verification

- `ng test --watch=false`: 24 archivos / 152 tests verdes, incluidos
  `cultivos.page.spec.ts` (conteo de `article`, botón `'Agregar'` por texto exacto, enlace
  `'A Sistema'` por orden del DOM) y `riego.page.spec.ts` (`button[data-energia]` con
  `<ng-icon>` adentro).
- `ng build`: exit 0, `Prerendered 2 static routes.`
- Capturas reales en Chromium headless con sesión sembrada en `localStorage` y backend local:
  `/cultivos` y `/riego` a 360, 768 y 1024, más dos capturas altas (360×1700) para ver la nav
  del wizard al final de la página. Observado: sin overflow horizontal en ningún ancho; a 360
  la nav es una columna de dos botones de ancho completo, la cabecera de proyecto envuelve la
  línea de referencia, el input de presupuesto deja el sufijo "Bs" adentro y el desplegable de
  catálogo no empuja al botón "Agregar"; a 1024 los tres paneles están intactos y la nav vuelve
  a una fila.
- Los archivos temporales de la maniobra de sesión (`environment.ts` apuntado al backend de
  prueba, `public/__seed.html`, `config.py` y `dev.db` del backend del worktree) se revirtieron
  o borraron antes de commitear.

## Deuda anotada

- Los tres pasos del wizard no comparten el valor del tope de los raíles: `terrain` y `riego`
  usan `calc(100vh-6rem)` y `cultivos` conserva su `calc(100vh-9rem)` original. Funciona en los
  tres casos, pero la misma pantalla de chrome merece un único valor; se deja así para no
  cambiar la geometría de escritorio de `cultivos` sin que el usuario lo pida.
