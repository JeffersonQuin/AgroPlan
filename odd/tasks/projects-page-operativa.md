# Página principal operativa: header limpio y tarjetas con el avance real

Quinta ronda de trabajo sobre el dashboard. Hasta hoy la grilla de proyectos funciona a medias:
el botón "Nuevo proyecto" es lo único vivo, el header muestra navegación y usuario inventados, y
cada tarjeta dice "Paso 1" con el terreno vacío aunque el proyecto tenga terreno, cultivos y
sistema guardados.

Branch: `feat/projects-page-operativa` (base `dev`).

## Specs

- **S1** En el header del dashboard se eliminan los ítems de navegación "Mis Proyectos", "Catálogo
  de Cultivos", "Calculadora Hidráulica" y "Documentación". Textual del usuario: «en el header
  elimina estas opciones "Mis Proyectos / Catálogo de Cultivos / Calculadora Hidráulica /
  Documentación"». No quedan enlaces muertos (`href="#"`) ni huecos de navegación.
- **S2** Se elimina el botón de notificaciones con su punto rojo. Textual: «Notoficaciones igual
  eliminalo». No hay campana, ni panel, ni contador simulado.
- **S3** El bloque de usuario del header deja de ser texto fijo: muestra el nombre y el apellido
  de la sesión real y al hacer click ofrece desloguear. Textual: «donde muestra el usuaroi su
  nombre y apellido que haya la opcion de desloguear al hacer click». La opción "Cerrar sesión"
  limpia la sesión y navega a `/login`.
- **S4** El nombre de la marca del header lleva siempre a `/projects`. Textual: «del header en el
  nombre que siempre lo lleve a la pagina princial /projects». Desde `/projects` recarga el
  dashboard; nunca deja la vista en el paso del wizard.
- **S5** Las tarjetas reflejan el avance y el terreno realmente guardados. Textual: «En los cards
  deberia mostrar los terrenos que ya estan guardados porque solo es queda en paso 1 estatico
  deber ir de acuerdo a como esta le avance y mostrar el area adecuada».
  El paso mostrado se deriva de los datos, no de la columna escrita a mano:
  1 = hay terreno guardado, 2 = hay al menos un cultivo, 3 = hay sistema de riego, 4 = hay una
  corrida del agente terminada. Un proyecto sin terreno queda en paso 1.
  - La vista previa dibuja el contorno del terreno guardado; sin terreno, el placeholder "Sin
    terreno definido" sigue apareciendo.
  - La superficie es el área real del terreno. Sin terreno dice "Sin definir": nunca "0.00 ha
    (0 m²)".
  - Las especies son los cultivos reales del proyecto.
  - La fila de riego muestra el tipo real y los sectores reales. Sin sistema dice "Sin definir".
  - La pendiente es la del terreno guardado.
  - El botón de la tarjeta abre el paso que corresponde al avance, no siempre `/terreno`.

## Tasks

- [x] T1 (S1-S4) Header del dashboard: fuera navegación y campana, marca a `/projects`, menú de
  usuario con "Cerrar sesión". Ruta: inline. Commit: `af184ac`. Verificación:
  `app-header.spec.ts` 7/7.
- [x] T2 (S5) Backend: derivar el avance desde las tablas y exponer en `GET /proyectos` lo que la
  tarjeta dibuja (`ultimo_paso_completado` derivado, `pendiente_pct`, `num_sectores`, `geometria`).
  Ruta: inline. Commit: `77422f7`. Verificación: `test_proyectos_listado_avance.py` 7/7 y la suite
  del backend completa 245/245.
- [x] T3 (S5) Frontend: modelo, store y tarjeta contra el contrato nuevo del listado; el click abre el
  paso real. Ruta: inline. Commit: `3f42ac2`. Verificación: specs de la feature 42/42 y la suite
  completa del frontend 195/195 en 29 archivos; `ng build` AOT sin errores.
- [x] T4 (S1-S5) Specs del dashboard y de la tarjeta actualizadas; contrato del listado documentado
  en `docs/flujo-sistema-agroplan.md`. Ruta: inline. Commit: este, que cierra la feature.
  Verificación visual a 1840, 1280 y 480 px: **no ejecutada**, no hay herramienta de captura en
  esta sesión; queda pendiente que la mire el usuario.

### Corte de entrega

La rama acumula ~7.5k líneas sobre `origin/main` en 23 commits: es una entrega para revisar por
partes. Este feature es la última unidad de la rama y no toca los anteriores más allá del contract
del listado, así que se puede publicar en un PR propio (o al final de la cadena) sin reescribir
historia.

## Log

- L1 (usuario, verbatim): «vale ahora crea un rama donde pondremos en funcionamiento todo la pagina
  principal @frontend/src/app/features/projects/projects.page.html , porque ahora solo funciona el
  boton de nuevo proyecto. Porque te digo que cosas no debe estar:
  1. en el header elimina estas opciones "Mis Proyectos
  Catálogo de Cultivos
  Calculadora Hidráulica
  Documentación"
  2. Notoficaciones igual eliminalo.
  3. donde muestra el usuaroi su nombre y apellido que haya la opcion de desloguear al hacer click.
  4. del header en el nombre que siempre lo lleve a la pagina princial /projects.
  5. En los cards deberia mostrar los [imagen] los terrenos que ya estan guardados porque solo es
  queda en paso 1 estatico deber ir de acuerdo a como esta le avance y mostrar el area adecuada.»
- L2 (evidencia): el header real del dashboard es `projects/components/app-header/app-header.ts`
  (navegación en `:34-55`, campana en `:76-82`, usuario fijo "Ing. Martín Rossi" en `:84-98`); el
  `wizard-header` de los pasos no tiene navegación ni campana y no se toca.
- L3 (evidencia): `GET /proyectos` devuelve `area_m2`, `cultivos_count`, `sistema_tipo` y la columna
  `ultimo_paso_completado`, que **nadie deriva de los datos**: solo la escribe un `PATCH`, y el
  wizard solo manda `nombre`. Por eso todas las tarjetas dicen "Paso 1".
- L4 (evidencia): el mapa de la tarjeta está en `projects/store/projects.store.ts` → `toProject`
  (`:130-166`) con `preview: 'empty'`, `crops: []`, `hydraulicSpecs: 'Sin definir'` y
  `sectorsLabel` que en realidad muestra el área del terreno.
- L5 (usuario, verbatim): «continua todo porque se colgo dejamos el odd abierto ten en cuenta que
  tengo 8 de ram asi que no hagas muchos testing cuando estes trabajando con a gentes en paralelo
  porque ahi se colgo».→ se retoma en serie: ninguna prueba en paralelo, una corrida por vez.
- L6 (evidencia): el runner del frontend no arranca con el Node del sistema (v22.22.2); el CLI de
  Angular 22 exige ≥ 22.22.3. Se corre con `npx -y node@22.22.3 node_modules/@angular/cli/bin/ng.js
  test`, sin tocar el proyecto.
- L7 (evidencia): `tests/test_proyectos_listado_avance.py` → 7 passed; `app-header.spec.ts` →
  7 passed.
