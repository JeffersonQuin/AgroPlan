# Pitch y demo de AgroPlan — 4 minutos + 4 de preguntas

Guion operativo para la presentación de hoy. Todo lo que está acá sale del estado real del
repositorio (`docs/flujo-sistema-agroplan.md`, `odd/tasks/paso1..paso4`, `backend/app/routers`,
`frontend/src/app/features`). Lo que todavía no existe está marcado como **contrato** o
**fuera de alcance**: no lo presentes como hecho.

> **Regla de oro de los 4 minutos:** el jurado no recuerda features, recuerda una decisión de
> diseño. Nuestra decisión es: **el LLM decide *qué y por qué*; el motor determinístico decide
> *dónde y cuánto*.** Todo el guion gira alrededor de esa frase.

---

## 0. Resumen ejecutivo (lo que tenés que poder decir en 20 segundos)

AgroPlan es un asistente de diseño agronómico para pequeños y medianos productores: el productor
dibuja su terreno, carga suelo, fuente de agua y caudal, y el sistema le devuelve **un plan de
cultivos y un diseño de riego por goteo con cifras verificables y trazables a fuentes**, listo
para imprimir.

Nadie más en el mercado local hace las dos cosas juntas: **recomendar con IA** y **calcular el
diseño con un motor determinístico auditable**.

---

## 1. La problemática

### 1.1 El problema en una frase

El pequeño productor agrícola decide **qué sembrar** y **cómo regar** con intuición, y cuando
quiere ahorrar agua no tiene quién le calcule el sistema: ni un agrónomo accesible, ni una
herramienta que le diga cuántos sectores, qué bomba, qué caudal real necesita.

### 1.2 Los cuatro dolores concretos

| # | Dolor | Qué pasa hoy en la práctica |
|---|---|---|
| D1 | **Decisión de cultivo sin datos** | Se siembra "lo que siempre se sembró" o lo que sugiere el vecino. No se cruza suelo, agua disponible, zona climática y presupuesto. |
| D2 | **El riego se improvisa** | Un sistema de goteo mal dimensionado se compra mal y se paga dos veces: bomba chica, sectores que no cierran, caudal que no alcanza en verano. |
| D3 | **Nadie calcula, todos opinan** | El consejo técnico es oral y no queda registro. No hay plano, no hay números, no hay forma de revisar la decisión seis meses después. |
| D4 | **La IA generativa "miente con formato"** | Un chatbot puede escribir un plan de riego perfectamente redactado con coordenadas y caudales inventados. Suena experto y es ficción. |

**D4 es el dolor que justifica la arquitectura.** Cualquiera puede hoy pegar un prompt en un
chatbot y sacar un "plan". Nuestro diferencial no es la IA: es **qué parte del resultado confiamos
a la IA y qué parte no**.

### 1.3 A quién le hablamos

- Pequeño y mediano productor que quiere instalar o ampliar riego por goteo.
- Técnico o vivero que arma la propuesta para el productor y necesita un plano y un informe.
- Instituciones de extensión agrícola que necesitan estandarizar propuestas.

> **Antes del pitch:** si vas a citar números de mercado (hectáreas, porcentaje de productores sin
> asistencia técnica, precio del goteo), cargalos de una fuente verificable y dejálos en la slide.
> No estimemos en vivo: un número inventado en la primera frase destruye la credibilidad de D4.

---

## 2. Cómo lo resuelve AgroPlan

### 2.1 La división de trabajo (la idea central)

```
Productor → backend valida y persiste → agente elige y justifica → motor calcula → informe + PDF
```

| Actor | Decide | NO hace |
|---|---|---|
| **Agente** (LLM con fuentes reales) | **Qué** cultivar y **por qué**; parámetros agronómicos y de riego sugeridos, con fuentes citadas | No devuelve geometría ni cifras de diseño final |
| **Motor determinístico** (Python puro) | **Dónde** va cada bloque, cuántos sectores, qué caudal, cuánto tiempo de riego, autonomía | No llama al LLM |
| **Backend** (FastAPI) | Valida, persiste, orquesta, degrada con advertencias | No dibuja |
| **Cliente** (Angular) | Captura, dibuja el contorno, pinta lo que el backend devuelve | No calcula áreas ni caudales |

Frase para decir en cámara: *"Si el agente devolviera coordenadas, el plano sería ficción con
formato de JSON. Por eso la geometría no la toca la IA."*

### 2.2 El flujo real, punta a punta

Wizard de cinco pantallas, una por slice:

1. **Proyectos** — lista, crea, duplica, elimina (soft delete).
2. **Terreno** — contorno dibujado + tipo de suelo + fuente de agua + caudal disponible (opcional).
   El backend deriva `area_m2`, `perimetro_m` y lados. **El cliente no calcula nada.**
3. **Agente** — productos deseados, presupuesto, energía disponible. Corrida asíncrona
   (`202` + polling con fase visible y cronómetro) → propuesta de cultivos con fuentes.
4. **Cultivos y riego** — reparto agronómico del área en bloques/zonas sobre el terreno, balance de
   área, y configuración de goteo, tanque, bomba, emisor y sectores.
5. **Resumen** — informe del agente + plano con terreno, zonas y sectores + PDF.

### 2.3 Los cuatro diferenciadores que sí se pueden demostrar

| Diferenciador | Cómo se prueba en la demo |
|---|---|
| **Motor determinístico auditable** | El mismo terreno produce siempre el mismo plano. Las cifras salen del motor, no del modelo. |
| **Trazabilidad de fuentes** | Cada recomendación apunta a fuentes reales persistidas; la corrida guarda modelo, versiones y tokens. |
| **Degradación honesta** | Si falta el caudal, el sistema **asume** un valor por tabla, lo marca como asumido y nunca bloquea al productor por un número que inventó el sistema. |
| **Corrida reproducible** | Cada corrida del agente se guarda con su `intake_hash`: se puede volver a inspeccionar qué se le pidió al modelo y qué respondió. |

### 2.4 Robustez que se puede mencionar en 15 segundos

- Si el modelo agrega un campo inesperado, **no tira la corrida**.
- Timeout configurable: el usuario no queda esperando para siempre.
- Sin credenciales del LLM, el pipeline funciona en **modo catálogo** (informe honesto, no inventado).
- Un modelo que no cumple el contrato se degrada con advertencia, no con excepción.

---

## 3. Guion minuto a minuto (4:00 exactos)

Reparto sugerido: **1 persona habla**, **1 persona opera la laptop** (no hables y tipees a la vez).
Si hay un tercero, es el que anota las preguntas del jurado para el bloque de Q&A.

| Tiempo | Bloque | Qué se dice | Qué se ve en pantalla |
|---|---|---|---|
| **0:00–0:20** | Gancho | "Un productor decide qué sembrar y cómo regar con la intuición del vecino. Y hoy cualquiera le pide a un chatbot un plan de riego: le va a responder con seguridad y con números inventados." | Slide con el título + la frase del problema. Nada más. |
| **0:20–0:50** | Problema | D1–D4 en 30 s: sin datos para elegir cultivo, riego improvisado, nada queda en papel, y la IA generativa miente con formato. | Slide de los 4 dolores (2×2). |
| **0:50–1:10** | Solución + tesis | "AgroPlan hace las dos cosas: un agente investiga y elige **qué y por qué**, y un motor determinístico calcula **dónde y cuánto**. La IA nunca toca la geometría." | Diagrama de un solo renglón: Productor → API → Agente → Motor → Informe. |
| **1:10–1:40** | Slice 1: Terreno | "Dibujo el contorno. El sistema deriva área y perímetro. Elijo suelo y fuente de agua. El caudal es opcional: si no lo sé, el sistema lo asume y lo marca como asumido." | Pantalla **Proyectos → Terreno**, contorno ya dibujado. |
| **1:40–2:20** | Slice 2: Agente | "Le digo qué quiere producir y con qué presupuesto. El agente investiga, elige cultivos y justifica con fuentes. Miren que la corrida se ve pasar de fase, con cronómetro." | Intake + modal de resumen previo + stepper de fases corriendo. |
| **2:20–2:55** | Slice 3: Cultivos y riego | "Esto es lo que devolvió: bloques con su polígono sobre el terreno, balance de área, demanda de agua. Acá está la bomba, el emisor y los sectores que calculó el motor." | Pantalla **Cultivos** (plano con zonas) → **Sistema de riego** (sectores). |
| **2:55–3:25** | Slice 4: Resumen | "Informe con balance hidráulico, presión, materiales y advertencias donde corresponde. Y el PDF para llevar a campo." | Pantalla **Resumen** + plano final; generar/abrir PDF. |
| **3:25–3:50** | Arquitectura y cierre | "Todo esto es auditable: cada corrida guarda modelo, versiones, tokens y fuentes. La IA decide qué y por qué; el motor decide dónde y cuánto. Eso es AgroPlan." | Slide final: la frase tesis + stack. |
| **3:50–4:00** | Cierre | "Se puede evaluar sin agrónomo y sin instalar nada. Gracias." | Slide con URL / QR. |

**Margen de seguridad:** tenés **0:20 de colchón** al final. Si te atrasás, el bloque que se
recorta es el 2:4 (robustez) — está fuera del guion hablado y sirve solo para Q&A.

---

## 4. Cómo mostrar los slices

Los "slices" son los cuatro pasos funcionales ya entregados del wizard. **No son cuatro
presentaciones: son un solo recorrido de un proyecto.** El jurado tiene que ver el proyecto
avanzando, no cuatro pantallas sueltas.

### 4.1 El hilo conductor

Decí una sola vez al principio: *"Voy a recorrer un proyecto real de punta a punta; son los cuatro
slices que construimos."* Después no vuelvas a explicar la navegación: hacé clic y contá lo que
importa.

### 4.2 Qué decir y qué NO decir por slice

| Slice | Doc de spec | Qué mostrar (1 acción) | Qué decir (una frase) | Qué NO mostrar |
|---|---|---|---|---|
| **P1 · Proyectos + Terreno** | `odd/tasks/paso1-frontend.md` | Elegir un proyecto ya creado y entrar directo a Terreno | "El contorno lo dibuja el productor; el área y el perímetro los deriva el backend, no el navegador." | El dibujo del polígono en vivo (se va en 40 s y no aporta) |
| **P2 · Cultivos + Agente** | `odd/tasks/paso2-cultivos.md`, `odd/tasks/agente-recomendaciones.md` | Abrir el intake, mostrar el resumen previo, disparar o mostrar la corrida | "El agente propone cultivos con fuentes; el intake que se le manda queda guardado con hash." | La espera real del modelo (ver §5.2) |
| **P3 · Sistema de riego** | `odd/tasks/paso3-riego.md` | Pantalla de riego con goteo, tanque, bomba y sectores | "El paso 3 solo recoge restricciones: energía, presupuesto, caudal. El diseño lo calcula el motor." | El modal de sectores completo (dejalo para Q&A) |
| **P4 · Resumen** | `odd/tasks/paso4-resumen.md` | Informe + plano + PDF | "Todas las cifras del informe las produce el motor; el agente las explica, no las inventa." | Scrollear el informe entero |

### 4.3 Las tres cosas que el jurado tiene que haber visto

1. Un terreno dibujado con **área derivada por el backend**.
2. Una **propuesta del agente con fuentes** y la corrida trayectoria/fases.
3. Un **plano final con sectores y un PDF**, con **advertencias** donde el sistema no puede afirmar algo.

Si el tiempo se cae, sacrificá P1 y P3 antes que estos tres.

---

## 5. La demo

### 5.1 Antes de entrar (checklist de 5 minutos antes)

- [ ] Backend arriba y respondiendo (`docs/flujo-sistema-agroplan.md` §14 para los contratos).
- [ ] Frontend servido; anotá el puerto real en un papel (no lo busques en vivo).
- [ ] **Un proyecto ya avanzado hasta Resumen, con corrida aplicada e informe generado.** Este es el
      proyecto que se recorre. No se construye en vivo.
- [ ] Un segundo proyecto a medio camino (solo Terreno) como respaldo si el primero falla.
- [ ] El PDF ya generado en el escritorio, por si el backend se cae al imprimir.
- [ ] Cerrar notificaciones, Slack, WhatsApp, y cualquier pestaña con correo.
- [ ] Zoom del navegador a ~125 % para que se lea desde el fondo del aula.
- [ ] Modo "no molestar" activo. Un popup en pantalla es lo que más rápido mata una demo.
- [ ] Cronómetro visible para el que habla (el operador avisa a los 2:00 y a los 3:00).

### 5.2 La decisión más importante: **no corras el agente en vivo**

Una corrida real del modelo tarda y depende de red y de credenciales. En 4 minutos no hay margen
para una espera incierta.

**Plan A:** mostrá la corrida **ya hecha** (informe generado) y el stepper de fases como evidencia
del mecanismo. Decí: *"esta corrida se hizo antes; lo que importa es que quedó guardada con su
intake y sus fuentes."*

**Plan B (solo si la latencia está probada hoy):** disparar la corrida en vivo con el stepper
corriendo, y mientras avanza, explicar el problema D4. Si en 25 s no termina, seguí hablando y no
vuelvas a esa pantalla.

### 5.3 Planes de contingencia

| Se cae… | Qué hacés |
|---|---|
| El agente / el LLM | "El sistema funciona en modo catálogo sin credenciales" — y mostrá el informe guardado. Es una feature, no una excusa. |
| El backend | Pasá al PDF ya generado y contá el contrato del plano. No reinicies nada en vivo. |
| Internet | Todo es local: backend, frontend y base. La demo no debería depender de red; si el jurado pregunta por la nube, es una respuesta de arquitectura, no un bloqueo. |
| El navegador | Segunda pestaña ya abierta en Resumen. Nunca recargues una app Angular en vivo con un formulario a medio llenar. |

---

## 6. Bloque de preguntas (4 minutos, ~8 preguntas)

Cada respuesta: **una frase de tesis + una prueba**. Máximo 25 segundos. Si la pregunta es ancha,
contestá y devolvé el foco.

### 6.1 Las que seguro preguntan

**"¿Qué pasa si el LLM se equivoca?"**
No puede romper el diseño: el agente propone cultivos y parámetros, el motor calcula. Si el modelo
devuelve un campo inesperado, la corrida no se cae; si no hay credenciales, el pipeline corre en
modo catálogo. Y todo queda guardado con modelo, versiones y tokens para revisarlo después.

**"¿De dónde saca los datos el agente?"**
De las fichas curadas del backend (suelo, cultivo, requerimientos) más las fuentes que declara. Las
fuentes se persisten con sus identificadores: una recomendación sin fuente es un bug, no una
opinión.

**"¿Por qué no dejaron todo en manos de la IA? Es más simple."**
Porque un plano tiene que ser reproducible. Con la IA calculando geometría, dos corridas dan dos
planos distintos y ninguno es auditable. El motor da determinismo; la IA da criterio.

**"¿Y si el productor no sabe su caudal de agua?"**
Es el caso más común y está resuelto: el sistema asume un valor de referencia según la fuente, lo
marca como `asumido` y **nunca** lo bloquea por un número que inventó el sistema. Solo bloquea si
el caudal informado por el productor no alcanza ni para el emisor más chico.

**"¿Qué pasa si el agua no alcanza para todo lo que quiere sembrar?"**
Hay una escalera de degradación: riego normal, riego nocturno extenso con advertencia, más
sectores y turnos, y si aún no alcanza, se reduce el área regada — con la advertencia explícita.
El sistema nunca entrega un diseño imposible en silencio.

**"¿Cómo validan que los cálculos están bien? ¿Hay tests?"**
El motor es Python puro y determinístico: mismo input, mismo output, testeable sin LLM. El cálculo
se prueba aislado del modelo, que es exactamente lo que permite confiar en el plano.

### 6.2 Las de alcance (contestá sin defender de más)

**"¿Funciona para cultivos X / para 50 hectáreas / con riego por aspersión?"**
Hoy está enfocado en riego por goteo para pequeña y mediana parcela. La arquitectura separa fichas
de cultivo, parámetros de riego y motor, así que ampliar el catálogo o el método de riego no toca
el núcleo. (Si insisten: nombrá el límite real y no prometas fecha.)

**"¿Qué falta para producción?"**
Fuera de alcance declarado en el PRD: catálogo de materiales editable, administración de precios,
roles y usuarios avanzados, versionado de proyectos, vista 3D, importación CAD y colaboración en
tiempo real. Tenemos el flujo completo, no el catálogo comercial completo.

**"¿Es un modelo entrenado por ustedes?"**
No. Es un pipeline con un modelo al que se le exige contrato y fuentes, y un backend que lo
verifica. No dependemos de entrenar nada propio, y eso nos deja cambiar de modelo sin rehacer el
producto.

**"¿Modelo de negocio?"**
Si esto no lo definieron todavía, la respuesta honesta es la de arquitectura: costo por corrida
bajo y medible (tokens por corrida guardados), y el valor está en el plano y el informe, no en el
chat. No inventes precios en el escenario.

### 6.3 Preguntas trampa y cómo salir

| Pregunta | Salida |
|---|---|
| "¿Esto lo hizo la IA por ustedes?" | "La IA escribió código; las decisiones de contrato —quién calcula qué, qué se bloquea y qué no— son nuestras y están documentadas en el repo." |
| "Demostrame que el cálculo está bien, ahora." | "Con gusto en el pasillo: el motor tiene tests determinísticos. Acá lo importante es que ese cálculo no depende del modelo." |
| "¿Por qué Angular y FastAPI?" | "Dibujo y formularios en el cliente, validación y cómputo en el servidor. La regla es que el cliente no calcule áreas ni caudales." |
| Si no sabés | "No lo tengo resuelto; lo anoto." Y el que anota, anota. Inventar en Q&A es lo único imperdonable. |

---

## 7. Reparto de roles

| Rol | Responsabilidad | Nota |
|---|---|---|
| **Orador** | Habla los 4 minutos, conecta cada slice con la tesis | Nunca toca la computadora |
| **Operador** | Clics preparados, avisa 2:00 / 3:00 / 3:45 | Practica el recorrido 3 veces con el orador |
| **Anotador** | Escribe las preguntas del jurado | Sirve para responder en orden sin pisarse |

Reglas de convivencia: **una sola voz por bloque**. Si el operador quiere corregir, levanta la mano;
no habla encima.

---

## 8. Ensayo: los tres pases obligatorios

1. **Pase en seco (sin público, cronómetro):** 4:00 clavados, sin mirar el teclado.
2. **Pase con falla inyectada:** el operador cierra el backend a mitad de la demo. Tienen que llegar
   al PDF guardado y terminar el guion igual.
3. **Pase con preguntas hostiles:** alguien del equipo hace las cuatro preguntas de §6.1 sin avisar
   el orden. Respuestas de 25 segundos, cronometradas.

Si el pase 1 sale en 5:00, no es un problema de oratoria: es que el guion tiene bloques de más.
Recortá el 0:20–0:50 (problema) a dos dolores, no a cuatro.

---

## 9. One-pager para tener al lado (imprimilo)

```
TESIS      La IA decide QUÉ y POR QUÉ. El motor decide DÓNDE y CUÁNTO.
PROBLEMA   Se siembra por intuición y el goteo se dimensiona mal. Y la IA
           generativa produce planes con números inventados.
PRUEBA     Terreno dibujado -> propuesta con fuentes -> plano con sectores -> PDF.
TRES COSAS Área derivada por el backend. Propuesta con fuentes reales.
QUE SE VEN Plano + PDF con advertencias honestas.
HONESTIDAD Caudal opcional: se asume y se marca; nunca bloquea por un
           número que puso el sistema.
NO DIGO    Precios, cuotas de mercado, ni features fuera del PRD.
CIERRE     "Se evalúa sin agrónomo y sin instalar nada. Gracias."
```

---

## 10. Riesgo de la presentación (lo que puede salir mal)

| Riesgo | Mitigación |
|---|---|
| Esperar al LLM en vivo | Plan A: corrida ya hecha (§5.2) |
| Presentar contrato como si estuviera hecho | Todo lo `[contrato]` de `docs/flujo-sistema-agroplan.md` se dice como diseño, nunca como funcionalidad en vivo |
| Sobrecargar de arquitectura | La arquitectura entra una sola vez, en 3:25, y solo como tesis |
| Inventar números en Q&A | Tabla de preguntas trampa (§6.3) + el anotador |
| Un integrante que no habló | Dale el bloque 0:20–0:50 (problema): es el más fácil de ensayar y el más difícil de arruinar |
