# Resumen: geometría real del terreno y recomendaciones legibles

Paso 4 del wizard: el informe tiene que trazar los sectores **dentro del área que dibujó el
cliente** y mostrar las zonas de cada producto. La lista de recomendaciones no puede mostrar
mensajes internos del pipeline.

Branch: `feat/resumen-geometria` (base `dev`). Persigue a `odd/tasks/paso4-resumen.md`.

## Specs

- **S1** Los sectores se trazan **dentro del polígono del terreno** que cargó el usuario, no
  dentro de su caja envolvente. Con un trapecio, las franjas de sector siguen el trapecio; el
  área de cada sector es área usable del polígono, no del rectángulo que lo contiene.
- **S2** Las zonas de cada producto (bloques) van **dentro del polígono** y se ven en el plano,
  cada una con su color y su etiqueta; la suma de sus áreas sigue siendo el área del terreno y
  ninguna zona puede caer fuera del polígono.
- **S3** El sistema de riego (matriz, laterales, goteros, válvulas) se calcula y dibuja
  **sobre los sectores reales**: ningún tramo, gotero ni válvula puede quedar fuera del
  polígono, y el cómputo de tubería y goteros sale de las longitudes y áreas recortadas.
- **S4** El plano del informe muestra, en este orden de lectura: el polígono del terreno, los
  sectores y las zonas de cultivo con su nombre y su color, y encima la red. Con leyenda que
  distinga cada cosa. Lo que está fuera del terreno no se dibuja.
- **S5** Las recomendaciones finales muestran sólo recomendaciones: nada de detalles internos
  del pipeline (`AGENTE_MODO`, "la corrida se resolvió con el catálogo interno", "se usó la
  siembra elegida…"), ni la misma frase repetida una vez por cultivo. Un título, un detalle y
  una justificación distintos, deduplicados.
- **S6** Cuando no queda ninguna recomendación real, la sección lo dice ("no informado") en vez
  de mostrar diagnósticos internos. Las advertencias técnicas siguen visibles en su banner, que
  es donde corresponden.

## Tasks

- [x] **T1** Geometría sobre el polígono real: recorte de franjas contra el terreno, sectores por área usable, zonas de cultivo dentro del polígono, red y cómputo sobre las áreas recortadas — S1, S2, S3
- [x] **T2** Recomendaciones legibles: filtrar diagnósticos internos, deduplicar y separar advertencias técnicas — S5, S6
- [x] **T3** Plano del informe: terreno + sectores + zonas con color y etiqueta, red encima, leyenda clara, nada fuera del polígono — S4

## Log

- **L1** (usuario) "hay varias cosas que mejorar del resumen" con dos capturas: la lista de
  recomendaciones finales repite "La corrida se resolvió con el catálogo interno. AGENTE_MODO
  está en 'catalogo'." y "Se usó la siembra elegida (2026-11-21) en lugar de la que propuso el
  agente." una vez por cultivo, con el mismo texto en detalle y justificación; y el plano muestra
  un rectángulo lleno de goteros, con 849 tramos y 4956,06 m de tubería.
- **L2** (usuario) "esta raro primeramente porque el poligono inicial no era ese, ademas no
  muestra las zonas donde deberia plantarse los 5 productos, ademas no sigue la imagen inicial.
  Te dije que debemos trazar los sectores dentro del area inicial que nos dio el cliente y de
  acuerdo a eso hacer tambien el sistema de riego."
- **L3** (evidencia) El terreno del usuario es un trapecio de 2100 m² con vértices
  `(0,40) (60,40) (60,20) (30,0) (0,0)`. Los sectores guardados son rectángulos de 7,5 × 40
  (`anillo [0,0]-[7,5,0]-[7,5,40]-[0,40]`), y los bloques de cultivo son bandas rectangulares
  de 60 × 7 que **incluyen área fuera del trapecio**. La causa está en
  `services/riego.py::_poligono_franja`, que usa `geometria.caja()` (caja envolvente) y devuelve
  un `rectangulo`, sin recortar contra el polígono; `geometria.py` no tiene recorte.
- **L4** (evidencia) Las recomendaciones del informe salen de `agente_recomendaciones` (filas
  tipo `advertencia`/`distribucion` que escribe el pipeline) y su `detalle` repite el título.
