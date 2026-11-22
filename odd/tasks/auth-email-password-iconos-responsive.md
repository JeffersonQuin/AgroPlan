# Login y registro con email/contraseña, iconos SVG y responsive

Habilitar el ingreso y el registro con correo y contraseña en las pantallas de auth
(hoy bloqueados porque el código asume que el backend sólo acepta Google), dejar Google como
vía principal, reemplazar los `<span class="material-symbols-outlined">` por iconos SVG de un
paquete instalado y hacer responsive el diseño de `/login` y `/register`.
Rama `feat/auth-email-password` creada desde `dev` en el worktree `AgroPlan-auth`.

## Specs

**S1** — Pedido del usuario, textual: *"arreglar la parte del login y resgitro
@src/app/features/auth/login-form.html y
@src/app/features/register/components/register-form/register-form.html donde puedas usr un
email para registrarse o loguearse porque ahora esta bloqueado"*. Concretamente: los campos
de email y contraseña dejan de estar `disabled`; se puede enviar el formulario y se llega al
mismo destino que el flujo de Google (`returnUrl` si empieza con `/`, si no `/projects`).

**S2** — Pedido del usuario, textual: *"quiero que hagas responsive el diseño porque no
esta"*. Aplica a `/login` y `/register`.

**S3** — Pedido del usuario, textual: *"los iconos instala una aplicacion para que use iconos
igaules en vez de span porque tarda en cargar y eso no deberia pasar"*. Decisión del usuario
sobre el paquete: *"@ng-icons + Material Symbols (SVG)"* — íconos iguales a los actuales,
inline SVG, sin request de fuente de Google en el render.

Convención de implementación de S3 (obligatoria para todas las pantallas):

- Se importa el set desde `@ng-icons/material-symbols/outline` (son los SVG outlined de
  Material Symbols) y se usa `<ng-icon [name]="..." [size]="..." />` de `@ng-icons/core`.
  Nunca `<span class="material-symbols-outlined">`.
- Los íconos se declaran en el componente que los usa con
  `providers: [provideIcons({ matFooOutline, matBarOutline })]`; no hay registro global, así el
  tree-shaking sigue funcionando y dos pantallas no comparten archivo.
- El tamaño del `<span>` original (`text-[18px]`, `text-[26px]`, …) pasa al input `size`
  (`size="18"`, `size="26"`). El color se hereda del texto (`fill="currentColor"` en el SVG),
  así que las clases `text-*` se mantienen en el elemento que envuelve al ícono.
- `aria-hidden="true"` se mantiene en íconos decorativos.
- Nombres que no existen en el set se reemplazan por el equivalente real y se informan: por
  ejemplo `expand_more` no existe como `matExpandMoreOutline`, se usa
  `matKeyboardArrowDownOutline`.
- Nombres dinámicos (un `signal`/propiedad que devuelve un nombre de ícono) se resuelven con un
  `const` map tipado de la clave dinámica al const del ícono importado, y todos los íconos del
  map se declaran en `provideIcons`.
- **El map debe devolver el nombre del ícono como string, nunca el const importado**, porque
  `provideIcons({ matFooOutline })` registra la clave `matFooOutline` cuyo valor es el SVG:
  `NgIcon` normaliza el `name` con `toPropertyName()` y busca esa clave
  (`@ng-icons/core/fesm2022/ng-icons-core.mjs:335-341,425-451`), así que recibir el SVG produce
  `No icon named … was found` y el ícono queda en blanco. Por la misma normalización, una clave
  con guion bajo (`lock_reset` → `lockReset`) no coincide: el valor que llega a `[name]` tiene
  que ser el nombre camelCase del ícono.
- No hay un segundo patrón aceptado: un mapa cuyas claves semánticas se registran tal cual y se
  pasan a `[name]` funcionaba sólo mientras ambas coincidieran, y se unificó en `133ce64`
  (`register-hero`, que ahora devuelve el nombre del registro como todos los demás).
- Cada grupo de íconos dinámicos tiene un test que exige que el `<ng-icon>` contenga un `<svg>`:
  sin eso, un nombre mal resuelto queda en blanco sin romper ningún test.
- Al final no queda ninguna referencia a `material-symbols-outlined` en `src/` ni el `<link>`
  de Google Fonts de Material Symbols en `src/index.html`.

**S4** — Pedido del usuario, textual: *"la princiapl siempre sera google la de email es por
si acaso"*. Google queda como vía primaria y visible sin scroll; email/contraseña es la
alternativa, no el camino principal.

**S5** — Pedido del usuario, textual, sobre el backend: *"Todavía no existe"*. El backend
FastAPI (`backend/app/routers/auth.py`) sólo expone `POST /auth/google` y
`POST /auth/google/register`. Por eso el contrato de email/contraseña se define en el frontend
y queda documentado en `src/app/features/auth/auth.model.ts` hasta que el backend lo
implemente; el frontend no inventa comportamiento que el backend simule.

**S6** — Pedido del usuario, textual: *"la rama que crearas saldra de dev"*. El trabajo vive
en la rama `feat/auth-email-password` creada desde `origin/dev` en un worktree aparte, sin
tocar la rama en la que trabaja el otro agente.

## Tasks

- **T1** — Contrato email/contraseña: `EmailCredentials`, `RegisterPayload` y la nota de
  contrato en `auth.model.ts`; métodos en `auth.api.ts`; `loginWithPassword` /
  `registerWithPassword` en `auth.store.ts`. Specs: S1, S5. Route: inline. Hecho en `3806e22`.
- **T2** — Formulario de login con email/contraseña habilitado, Google como vía principal.
  Specs: S1, S4. Route: inline. Hecho en `3806e22`.
- **T3** — Formulario de registro con email/contraseña habilitado (nombre, email, rol,
  contraseña, confirmación, términos). Specs: S1, S4. Route: writer. Hecho en `da94b83`.
- **T4** — Migración de iconos a `@ng-icons/core` + `@ng-icons/material-symbols` en todas las
  pantallas afectadas. Specs: S3. Route: inline (`auth/**`) + writer
  (`projects/**`, `cultivos/**`, `riego/**`, `terrain/**`, `wizard/**`). Dependencia en
  `d7eb642`; auth en `3806e22`; registro en `da94b83`; resto del app y quita de la fuente en
  `4bda26d`.
- **T5** — Responsive de `/login` y `/register` (móvil, tablet, desktop). Specs: S2.
  Route: inline + writer. Hecho en `3806e22` (login) y `da94b83` (registro).
- **T6** — Verificación. Specs: S1-S5. Route: verify + inline. Ver abajo.

## Verification

- `ng test --watch=false` (Node 24.22.3 de `/tmp`): 22 archivos / 143 tests, todos verdes,
  incluidos `auth/login-form.spec.ts`, `auth/auth.store.spec.ts` y
  `register/test/register-form.spec.ts`.
- `ng build`: el proyecto compila sin diagnósticos de TypeScript ni de templates y emite
  todos los bundles. El paso de prerender falla por un problema **preexistente** en la
  configuración de rutas del servidor (`The 'proyectos/:proyectoId/riego' route uses
  prerendering and includes parameters, but 'getPrerenderParams' is missing`), que se
  reproduce igual sobre `HEAD` limpio y que este trabajo no toca: el diff no modifica
  `app.routes.ts` ni la configuración de rutas del servidor.
- Chequeo estructural propio: cero `material-symbols-outlined` en `src/`, cero `<link>` de
  Material Symbols en `index.html`, cero regla `.material-symbols-outlined` en `styles.css`,
  y cada `<ng-icon name="matX">` estático tiene `matX` declarado en el `provideIcons` del
  componente que lo renderiza.
- Los seis `[name]` dinámicos se revisaron a mano: los cinco mapas tipados declaran todos sus
  valores en `provideIcons`, y el ternario de visibilidad de contraseña usa los dos íconos
  declarados.

## Commits

- `d7eb642` — `build(deps)`: `@ng-icons/core` + `@ng-icons/material-symbols`.
- `3806e22` — `feat(auth)`: login con correo y contraseña + responsive de `/login` + íconos de
  `auth/**` + eliminación de `LoginPasswordField`.
- `da94b83` — `feat(register)`: registro con correo y contraseña + responsive de `/register` +
  íconos de `register/**`.
- `4bda26d` — `refactor(icons)`: 61 spans del resto del app a SVG inline y quita de la fuente.
- `8fc881a` — `fix(icons)`: los cuatro grupos dinámicos resuelven el nombre del registro (S3).


## Log

**L1** — Pedido original del usuario, textual: *"vale ahora otro agente esta trabajando en
esta rama asi que nosotros haremos un worktree para arreglar la parte del login y resgitro
@src/app/features/auth/login-form.html y
@src/app/features/register/components/register-form/register-form.html donde puedas usr un
email para registrarse o loguearse porque ahora esta bloqueado ademas quiero que hagas
responsive el diseño porque no esta y los iconos instala una aplicacion para que use iconos
igaules en vez de span porque tarda en cargar y eso no deberia pasar. Alguna pregunta? la rama
que crearas saldra de dev."*

**L2** — Decisión del usuario sobre el backend FastAPI: *"Todavía no existe"*. Se define el
contrato en el frontend y queda documentado (S5).

**L3** — Decisión del usuario sobre los iconos: *"@ng-icons + Material Symbols (SVG)"*.

**L4** — Decisión del usuario sobre Google: *"la princiapl siempre sera google la de email es
por si acaso"*.

**L5** — Evidencia: el backend FastAPI (`backend/app/routers/auth.py:80,90`) sólo declara
`POST /auth/google` y `POST /auth/google/register`; no hay rutas de correo. Confirma S5.

**L6** — Evidencia: la fuente de Material Symbols se carga en `frontend/src/index.html:14-18`
y la regla `.material-symbols-outlined` vive en `frontend/src/styles.css:154-162`; hay 79
referencias a `material-symbols-outlined` en 22 archivos de `frontend/src`. Quitar el `<link>`
obliga a migrar todas, no sólo login y registro, o el resto de las pantallas se queda sin
íconos.

**L7** — Evidencia: `@ng-icons/material-symbols@36` ya no exporta los SVG en la entrada
principal (sólo `withMaterialSymbolsOutlined()`), los íconos SVG están en el subpath
`@ng-icons/material-symbols/outline` con nombres `mat<Name>Outline` y `mat<Name>FillOutline`.
`expand_more` no existe en ese set: se usa `matKeyboardArrowDownOutline`.

**L8** — Decisión técnica: los íconos se declaran por componente con
`viewProviders: [provideIcons({...})]`, sin registro global, para no crear un archivo
compartido entre pantallas ni romper el tree-shaking.

**L9** — Decisión técnica: `LoginPasswordField` existía sólo para el campo deshabilitado del
login; el campo se integra al formulario de `login-form` y el componente se elimina (S1).

**L10** — Entorno: el Node del sistema (v22.22.2) es menor al mínimo del Angular CLI
(^22.22.3). La verificación se corre con Node 24.22.3 descargado en
`/tmp/node-v24.22.3-linux-x64` (`export PATH=/tmp/node-v24.22.3-linux-x64/bin:$PATH`), sin
tocar la instalación del sistema.

**L11** — Resultado de las unidades delegadas: el writer de `projects/**` + `cultivos/**` +
`riego/**` + `terrain/**` + `wizard/**` migró 61 spans sin sustituciones de nombre; el writer
de `register/**` implementó el formulario con Signal Forms y reescribió su spec. Sus dos
comandos de verificación quedaron rojos por causas fuera de su alcance (un error de tipos en
`auth/login-form.spec.ts`, mío, y el prerender preexistente), y ambas se corrigieron o se
acotaron acá.

**L12** — Evidencia: `ng build` falla en el paso de prerender en `HEAD` limpio exactamente
igual (`proyectos/:proyectoId/riego` sin `getPrerenderParams`). El diff no toca rutas ni
configuración del servidor, así que es un bloqueo de entrega preexistente de `dev` y queda
fuera de esta tarea.

**L13** — Evidencia: `ng test --watch=false` con Node 24.22.3 → 22 archivos, 143 tests verdes.

**L14** — Limpieza: prettier reformateó archivos fuera del alcance (specs, `google-sign-in`,
`terrain-canvas`, `*-api.ts`, stores y previews). Se revirtieron para que el diff contenga
sólo los cambios de la tarea.

**L15** — Hallazgo del verificador independiente: S3 fallaba en cuatro grupos de íconos
(`project-card` cabecera y estado, `riego-form` energía, `terrain-summary` validaciones y
`form-field` `lock_reset`) porque los mapas devolvían el SVG en lugar de la clave del registro,
y `lock_reset` no sobrevive la normalización a `lockReset`. El chequeo estructural propio no lo
detectaba porque validaba que el componente mencionara el ícono, no que el `name` binding
coincidiera con una clave registrada. Corregido en `8fc881a`.

**L16** — Evidencia: `ng test --watch=false` → 22 archivos / 147 tests verdes y cero warnings
`No icon named`. Los cuatro tests nuevos fallan sobre el código anterior (4 failed / 25 passed,
nueve warnings) y pasan después: son la prueba durable de S3.

**L17** — Riesgo residual aceptado: `register-hero` registra sus cuatro capacidades bajo claves
semánticas propias; funciona y queda documentado como patrón alternativo en S3. Si se renombra
una de esas claves, el ícono queda en blanco, y ese grupo no tiene test propio: queda anotado
como deuda.

**L18** — Cierre de la deuda de L17: `133ce64` unificó `register-hero` a la convención de los
demás mapas (`FEATURE_ICONS` devuelve el nombre del registro y el template bindea el valor
mapeado) y agregó `register-hero.spec.ts`, que exige un `<svg>` en el ícono del pill y en los
cuatro de capacidad. La nota de S3 ya no describe un patrón alternativo; el Log conserva L17
como registro histórico de lo que estaba mal.
