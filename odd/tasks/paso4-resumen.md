# Paso 4 — Resumen final (informe del agente)

Paso 4 del wizard: el informe final donde el agente decide y el motor dibuja. Es el paso que decide
si la app sirve. Se ve como `frontend/paso4.html` (prototipo sin versionar), lleno con datos reales.

Branch: `feat/paso4-resumen` (base `dev`). Entrega en **5 cortes**, cada uno con su PR y verificación.

## Specs

- **S1** El paso 4 se ve como `frontend/paso4.html`: mismo layout de tres columnas y mismas secciones
  —datos del terreno, zonificación agronómica con imágenes, tecnología y cabezal, plano 2D con la red
  hidráulica, balance hidráulico, cómputo de materiales, calendario agronómico y recomendaciones
  finales— llenas con datos reales de la corrida.
- **S2** El paso 4 se dispara con un botón y un modal que **muestra el resumen previo completo**
  (terreno, productos, siembra y restricciones) antes de generar, "para que revise todo a detalle si
  está bien antes de generar". Se genera **una sola vez**; regenerar queda para plan premium.
- **S3** El agente produce **todas** las cifras del informe: balance hidráulico, presión de trabajo,
  turnos por sector, autonomía del tanque, eficiencia, demanda pico por cultivo, calendario,
  materiales con precios y recomendaciones. Cuando el motor tenga que ajustar sectores o red para
  cubrir esas cifras, **el ajuste se muestra al usuario** con qué cambió, de qué valor a qué valor y
  por qué.
- **S4** Imágenes híbridas: la ficha curada del backend lleva la imagen del cultivo; el agente
  investiga las que falten (equipo de cabecera y productos fuera de catálogo) y la URL queda guardada
  en la corrida con su atribución. Sin imagen, placeholder con la inicial y el color del cultivo.
- **S5** El contexto del agente incluye **la documentación ya modelada en la base**: del cultivo
  `kc`, `aptitud_suelo`, `profundidad_raiz_cm`, `densidad_plantas_m2`, `meses_siembra` y `fuentes`;
  del suelo `infiltracion_mm_h` y `retencion_agua_mm_m`; del terreno `lados_m`, `geometria.vertices`,
  `perimetro_m` y `profundidad_nivel_dinamico_m`; y las restricciones del paso 3 (energía, tanque,
  presupuesto). Nada modelado queda sin usar.
- **S6** El agente busca **precios con fuentes** para los materiales y **guarda en la base lo que
  encontró** (material, unidad, precio, moneda, fuente y fecha) para reutilizarlo en corridas de
  otros usuarios; un precio vencido se vuelve a investigar. El informe compara el total del cómputo
  contra el presupuesto del paso 3.
- **S7** `agente_recomendaciones` y `agente_fuentes` —hoy escritas y nunca leídas— se usan en el
  informe: recomendaciones finales con su justificación, y la lista de fuentes web consultadas.
- **S8** "Exportar PDF" y "Descargar Informe Técnico Completo" descargan un PDF **generado en el
  backend** (`POST /proyectos/{id}/pdf`, ya especificado en `docs/flujo-sistema-agroplan.md:704-731`)
  con la marca de agua "Estimación preliminar".
- **S9** Las cifras que el prototipo muestra y hoy no expone la API —presión, turno por sector,
  autonomía, demanda pico por cultivo, calendario, cómputo completo (tanque, bomba, conexiones) y
  eficiencia— viajan en `ResultadoProyectoOut` junto con las advertencias de ajuste de S3.
- **S10** Nada del informe se inventa: el plano sale de `red` real (nodos, tramos y emisores) y la
  IA nunca devuelve coordenadas. Un dato que no existe se muestra como "no informado", nunca como
  cero.

## Tasks

- [x] **T1** Contrato del agente: `EntradaAgente` con las fichas completas, terreno y restricciones; `PropuestaAgente` con cifras, materiales con precios y fuentes, recomendaciones e imágenes; prompt actualizado — S4, S5, S6 (contrato) — commit `fce6fec`
- [x] **T2** Motor se ajusta y resultado extendido: aplicar las cifras del agente, recalibrar sectores/red, grabar y exponer los ajustes; caché de precios en la base; `ResultadoProyectoOut` con S9; leer recomendaciones y fuentes — S3, S6 (persistencia), S7, S9 — commits `bafaa1e`, `2e22b8c`
- [x] **T3** Imágenes: `cultivos.imagen_url` + `imagen` en las fichas, URLs sembradas para el catálogo, atribución por fuente y fallback — S4 — commits `07b926b`, `5ae1603`, `6e76353` (PR #26)
- [x] **T4** Pantalla del paso 4: ruta, tienda, modal de resumen previo, corrida con estados, y todas las secciones del prototipo con el plano desde `red` — S1, S2, S9 (consumo) — commits `d050d15`, `614c385`, `4a7a4c9` (PR #29)
- [x] **T5** PDF del informe en el backend y botones conectados — S8 — commit `24ed8ad` (PR #30)

## Log

- **L1** (usuario) "perfecto ahora pasaremos al paso 4 que es el resumen la parte mas importante del
  proyecto, tanto como el agente y demas ya tenemos @frontend/paso4.html , y quiero que se vea igual
  la salida de lo que el agente debe hacer y demas todo similar. alguna pregunta? . Por cierto
  mjestra imagenes y lo que sugiero es que el agente saca las url de los productos y de la tecnologia
  y cabezal para que vaya con el prototipo. hazme preguntas?"
- **L2** (usuario) Imágenes: "Híbrido: ficha primero, agente si falta".
- **L3** (usuario) Disparo: "sera un boton con modal pero ahi debe darle el resumen antes de generar
  para que revise todo a detalle si esta bien antes de generar"
- **L4** (usuario) Cifras: "me gustaria que el agente haga todo porque el tendra toda la informacion
  y podra armar la respues de manera coherente"
- **L5** (usuario) Alcance: "las 3 primeras opciones, y ademas ten en cuenta que no estamos
  expltando la documentacion ni las recomendaciones que modelamos en la Db asi que todo eso sacale
  el maximo provecho aca ya que es al resumen final la manera que se sabe si una app es buena o no"
- **L6** (usuario) Conflicto de cifras: "el agente manda y el motor se ajusta pero al ajustar debe
  mostrar ese informacion al usuario porque es iportante saberlo"
- **L7** (usuario) PDF: "PDF generado en el backend".
- **L8** (usuario) Precios: "el agente busca precios y fuentes y gurda en db lo que encontro para
  futuras generaciones de otros usuarios"
- **L9** (usuario) Entrega: "5 cortes en orden (recomendado)".
- **L10** (evidencia) El prototipo `frontend/paso4.html` no calcula nada: todas sus cifras están
  hardcodeadas y sus 3 imágenes son hotlinks efímeros de Google AI-Studio, sin fallback.
- **L11** (evidencia) Brecha backend: `EntradaAgente` no lleva fichas ni geometría;
  `PropuestaAgente` no tiene cifras, materiales, precios, recomendaciones ni imágenes;
  `agente_recomendaciones` y `agente_fuentes` se escriben y nunca se leen; no existe generador de PDF
  ni catálogo de materiales; `ResultadoProyectoOut` no expone presión, turnos, autonomía, demanda pico
  ni calendario.
- **L12** (verificación T1) S4, S5 y S6 (contrato) en `pass`; compatibilidad de corridas viejas y de bodies previos confirmada, `intake_hash` sigue reutilizando la corrida y las restricciones generan una nueva. Correcciones aplicadas: dos ISC004 en el prompt, orden de imports, `moneda` en `MaterialAgente` y la regresión que descartaba `area_deseada_m2` para cultivos fuera de catálogo. Se adoptaron los 3 tests de compatibilidad del verificador (`test_agente_compatibilidad_paso4.py`). Suite: 109 tests verdes, `ruff` en el baseline.
- **L13** (advisory para T3) El prompt pide usar la imagen curada "sólo si la ficha no traía imagen", pero la imagen curada todavía no viaja en el contexto: T3 tiene que inyectar `cultivos.imagen_url` en la entrada para que la regla sea verificable.
- **L14** (verificación T2 A) S7 en `pass`, S3 y S9 en `pass` tras corregir tres blockers: el caudal por sector salía del preview y no de la red (3.0 vs 2.666 m³/h), sólo se comparaba el primer turno (dos sectores divergían en silencio) y los materiales con unidad `"Metro lineal"` o rubro `Válvulas` no se contrastaban. También se corrigió el motivo que afirmaba un recorte al rango 1..8 cuando el motor usó `num_sectores`, y el borde flotante de la tolerancia.
- **L15** (verificación T2 B) S6 en `pass` con revive en `pass` de sus cinco cláusulas. Blocker real corregido: dos materiales que sólo diferían en espacios internos rompían el commit con `IntegrityError` y **dejaban la corrida en `corriendo` para siempre**; ahora el lote se deduplica y cualquier fallo de persistencia deja la corrida en `error`. Además la clave unifica unidades y el prompt lleva sólo precios de familias de riego (hasta 40), no los 200 vigentes.
- **L16** (entrega) Los cortes 1 y 2 se publicaron como PRs encadenados: #22 `feat/paso4-contrato` → `dev` (T1) y #23 `feat/paso4-motor` → #22 (T2). Los cortes 3-5 se encadenan sobre `feat/paso4-motor`.
- **L17** (verificación T3) S4 en `pass` sin blockers. Migraciones probadas en cadena: `upgrade head` (+no-op), `alembic check` sin pendientes y `downgrade` conservando las 8 filas del catálogo con hash idéntico. Atribución de las 14 fotos comprobada contra Commons. Hallazgo corregido: el alta de un cultivo desde ficha curada (`arroz` escrito a mano) creaba la fila del catálogo sin imagen ni crédito.
- **L18** (entrega) PRs mergeados a `dev`: #22 (contrato, `176d92c`), #23 (motor y resultado, `7d79f54`), #26 (imágenes, `f25de0d`). Quedan los cortes 4 (pantalla) y 5 (PDF).
- **L19** (verificación T4) S1, S2, S3, S7, S9 y S10 en `pass`. Blocker corregido: el backend entrega la misma advertencia en `resultado.advertencias` y en `diseno.advertencias`, así que el banner la pintaba dos veces y la clave del `@for` se duplicaba; ahora se deduplica por código y mensaje. Advisory corregido: con el terreno caído, el modal mostraba `m²` y `m³/h` sin valor. El prototipo trae cotas, brújula y camino perimetral que la red no modela: no se dibujan para no inventar geometría.
- **L20** (verificación T5) S8 en `pass` para los dos botones y la marca de agua en todas las páginas. Blockers corregidos: `incluir` aceptaba cualquier clave en silencio y `["plano"]` devolvía un PDF de 2 KB casi vacío; ahora una clave no soportada responde 422 con las válidas, y `incluir: []` devuelve el informe completo. `reportlab 5.1.0` es Python puro, el lock verifica offline y la única transitiva nueva (`pillow`) no se usa: el PDF no descarga imágenes.
- **L21** (pendiente) El plano 2D no se dibuja dentro del PDF (el documento no embebe geometría). Está declarado como pendiente en `CLAVES_PENDIENTES` y se rechaza explícitamente en `incluir`; si se quiere el plano en el PDF, es trabajo aparte.
