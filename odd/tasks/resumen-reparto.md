# Resumen: reparto agronómico del área, plano legible y modo catálogo honesto

Cuarta ronda de ajustes del informe del paso 4, sobre lo que se vio al probarlo.

Branch: `fix/reparto-y-plano` (base `dev`). Persigue a `odd/tasks/resumen-geometria.md`.

## Specs

- **S1** El reparto del área **no puede ser partes iguales**. Cada producto recibe un área según su
  necesidad agronómica —demanda de agua, ciclo, densidad de plantas y la prioridad que eligió el
  usuario— y el reparto completo respeta el caudal disponible del terreno: la demanda pico del
  conjunto no puede superar lo que la fuente entrega en una jornada de riego. Con el agente en
  modo LLM, el área que propone el agente manda; en modo catálogo rige este cálculo.
- **S2** Las zonas de cultivo son **polígonos irregulares** que siguen el contorno del terreno y
  suman exactamente su área; no son bandas de un mismo ancho repartidas por igual. Dos productos
  con áreas distintas tienen zonas de superficies distintas, y la forma acompaña al terreno.
- **S3** El informe no muestra una pared de "no informado": si la corrida se resolvió **sin
  credenciales** (modo catálogo), lo explica una sola vez y con lenguaje de producto, y las
  secciones que dependen del modelo (cifras del agente, precios, fuentes) lo dicen en
  consecuencia, no como error.
- **S4** El plano prioriza la **red de riego** —matriz, tubería secundaria y laterales— y las
  zonas de producto con su color. Los emisores son ruido secundario: no se dibujan por defecto y
  se pueden encender.
- **S5** "Fuentes consultadas" muestra la investigación real cuando existió, con URL y fecha. Si
  no hubo investigación (modo catálogo), lo dice explícitamente en vez de aparecer vacía.

## Tasks

- [ ] **T1** Reparto agronómico y zonas irregulares: criterio documentado por producto, techo de caudal, y formas que siguen el terreno — S1, S2
- [ ] **T2** Informe honesto en modo catálogo, plano con prioridades visuales y fuentes explicadas — S3, S4, S5

## Log

- **L1** (usuario, con capturas) "hay mas cosas que mejorar del resumen: 1. porque muestra [Tecnología
  y Cabezal] no informada. 2. [Balance] igual no informado. 3. [Cómputo] no te muestra el
  presupuesto. 4. En fuentes consultadas no investigo nada de internet. 5. [Plano] me gusta como se
  ve pero porque hay tanto puntos azules? porque lo mas importante es la tuberia principal, lateral
  de goteo, y tuberia secundaria. Tambien el tanque y las bombas, pero lo que quisiera es que
  muestre mas el color de fondo del producto porque todo se ve medio azul. Y como te dije
  anteriormente la division solo lo hace diviendo el area sobre el numero de productos y no es asi,
  debe salir como esta imagen [prototipo] como ves las areas que se pintan no son partes iguales
  sino son irregulares dependiendo al producto algunos necesitan mas campo o otros no y por eso te
  dije investiga y cuando tengas esa informacion repartas el area en todos lo productos de manera
  eficiente"
- **L2** (evidencia) La corrida guardada tiene `modelo = 'catalogo'` y la advertencia
  `AGENTE_SIN_CREDENCIALES`: el proceso corriendo no tiene la clave del modelo, así que `cifras`
  viene con todo en `null`, `materiales` vacío, cero recomendaciones y sin investigación web. Eso
  explica los puntos 1 a 4: no es que el informe los oculte, es que el agente no los produjo.
  `.env` no se recarga con `--reload`: hay que reiniciar el proceso para que tome las credenciales.
- **L3** (evidencia) El reparto en modo catálogo asigna el mismo porcentaje a todos los productos:
  la corrida del usuario tiene cebolla, lechuga, maíz, yuca y maní con **420 m² cada uno**.
