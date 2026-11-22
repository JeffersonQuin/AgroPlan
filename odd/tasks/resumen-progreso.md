# Resumen: progreso visible del agente

Mientras el modelo tarda, el usuario tiene que ver que el proceso avanza. Sin porcentajes
inventados: las fases que el backend realmente ejecuta, con un cronómetro en la que está corriendo.

Branch: `feat/resumen-progreso` (base `dev`).

## Specs

- **S1** La corrida del agente expone su **fase actual** y desde cuándo está en ella, con estas
  fases reales y en este orden: `contexto` (arma el intake y el prompt), `modelo` (consulta al
  modelo; es la larga), `validacion` (sanea la propuesta), `precios` (caché y totales del cómputo),
  `red` (genera sectores y red), `listo`. Ninguna fase es decorativa: cada una se marca cuando el
  backend realmente la empieza.
- **S2** La pantalla del paso 4, mientras espera, muestra las fases con **check** en las cumplidas
  y la actual con un indicador animado y un **cronómetro** que cuenta desde que el backend entró en
  esa fase. Pasados 20 s en la fase del modelo, un texto explica que el modelo puede tardar uno o
  dos minutos y que la corrida sigue viva.
- **S3** La espera se sigue cortando a los 5 minutos con el mensaje actual, y si la corrida falla
  se muestra el error con la fase donde quedó, no un mensaje genérico.
- **S4** El cronómetro se calcula desde `fase_desde` del servidor, no desde que el navegador
  empezó a mirar: recargar la página no reinicia el conteo ni lo infla.

## Tasks

- [ ] **T1** Backend: columnas `fase` y `fase_desde` en `agente_corridas` (migración), actualización
  en cada paso de `ejecutar_corrida`, y exposición en `CorridaOut`/`CorridaDetalleOut` — S1
- [ ] **T2** Frontend: stepper de fases con checks y cronómetro, mensaje de espera larga y error con
  la fase donde quedó — S2, S3, S4

## Log

- **L1** (usuario) "como se que esta haciendo el modelo porque el usuario puedo pensar igual que yo
  que se colgo porque tarda mucho, hay alguna manera de mostrar eso? … quisiera algo visual para que
  el cliente sepa que no se colgo como 'analizand' luego un check y asi mostrando que esta
  avanzando es posible?"
- **L2** (usuario, decisión) "Fases reales con cronómetro", sin barra de porcentaje estimada.
- **L3** (usuario, decisión) Sobre la velocidad: "dejemoslo asi, si ya hay eso del progreso entonces
  esta bien dejarlo asi". No se toca el contrato del agente ni el modelo.
- **L4** (evidencia) Corrida real exitosa: `deepseek-v4.1-flash`, **88,5 s**, 15.954 tokens de
  entrada y 9.712 de salida. La fase del modelo es la que domina la espera.
