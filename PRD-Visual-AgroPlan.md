# PRD Visual — AgroPlan

> Documento de definición visual y funcional de las pantallas del wizard de AgroPlan.
> Cubre **únicamente las pantallas que faltan**: la pantalla `/proyecto/:id/resultado` (paso 4) ya existe.
>
> Versión: 1.0 · Abstracthon 2026 · Estado: propuesta para revisión

---

## 0. Alcance y contexto

La captura `principalAgroPlan.jpeg` corresponde al **paso 4 (Resultado)** de un wizard de cuatro pasos:

| # | Pantalla | Estado |
|---|---|---|
| 0 | Proyectos | a construir (mínimo indispensable) |
| 1 | Terreno | a construir |
| 2 | Cultivos | a construir |
| 3 | Sistema | a construir |
| 3.1 | Sectores (modal) | a construir |
| 4 | Resultado | **ya existe** — se usa como referencia visual |

El producto es **agrícola** (parcela, cultivos, riego por goteo), no un editor de instalaciones sanitarias.

**Fuera de alcance de este documento:** catálogo de materiales editable, administración de precios, usuarios/roles/login, versionado de proyectos, vista 3D, asistente de IA, importación CAD, colaboración en tiempo real.

---

## 1. Sistema de diseño

Derivado de la captura existente. Toda pantalla nueva debe reutilizarlo sin inventar tokens.

### 1.1 Tokens

| Token | Valor | Uso |
|---|---|---|
| `--verde-900` | `#14532D` | header, títulos de tarjeta |
| `--verde-700` | `#166534` | botón primario, stepper activo |
| `--verde-600` | `#2E7D32` | barra de título del canvas |
| `--verde-100` | `#E8F5E9` | chips, fondos suaves |
| `--fondo` | `#F6F8F6` | fondo de aplicación |
| `--borde` | `#E2E8E2` | bordes de tarjeta |
| `--texto` | `#1F2937` | texto principal |
| `--texto-suave` | `#6B7280` | texto secundario |
| `--alerta-bg` | `#FFF8E1` | tarjeta "Recomendaciones" |
| `--alerta-icono` | `#F59E0B` | icono de recomendaciones |
| `--error` | `#DC2626` | validaciones bloqueantes |
| `--warn` | `#D97706` | advertencias no bloqueantes |
| Radio tarjeta | `12px` | |
| Radio chip | `8px` | |
| Radio pill | `999px` | |
| Tipografía | Inter | base 13px · título de tarjeta 15px/600 · stepper 13px/600 |
| Sombra | `0 1px 2px rgba(0,0,0,.05)` | tarjetas |

### 1.2 Grid

- Header fijo: **64px**.
- Cuerpo: `300px | 1fr | 320px`, `gap: 16px`, `padding: 16px`.
- Breakpoints: bajo **1280px** el panel derecho colapsa a tabs inferiores; bajo **1024px** se apila en una columna con el formulario primero.

### 1.3 Patrón de layout por tipo de paso

| Pasos 1–3 | Paso 4 (existente) |
|---|---|
| Izquierda: **formulario de entrada** | Izquierda: resumen de solo lectura |
| Centro: **canvas 2D vivo** | Centro: canvas 2D |
| Derecha: **salida calculada + validaciones** | Derecha: resultados y cómputo |

El cambio de rol del rail izquierdo es deliberado: en los pasos 1–3 todavía hay algo que entrar.

### 1.4 Regla transversal de datos

> **La geometría es la única fuente de verdad.**

Áreas, perímetros, longitudes, cotas y caudales **nunca se escriben a mano**: se derivan de la geometría y se muestran como valores de solo lectura. Si un campo derivado se puede editar, el cómputo del paso 4 se desincroniza y la demo se rompe.

### 1.5 Componentes compartidos

| Componente | Descripción |
|---|---|
| `AppHeader` | logo + tagline, stepper, `Exportar PDF` (outline), `Guardar` (sólido) |
| `Stepper` | 4 pasos, círculo numerado, línea conectora, activo en verde con subrayado, pasos completados con ✓ |
| `Card` | contenedor blanco, borde `--borde`, radio 12px, título con icono en verde |
| `CanvasCard` | tarjeta del plano con barra de título verde y toggle `Plano 2D \| Detalles` |
| `LegendCard` | leyenda flotante bajo el canvas |
| `BalanceBar` | barra de progreso con estado verde / ámbar / rojo |
| `ValidationList` | lista de checks ✓ / ⚠ / ✕ con texto |
| `StepperFooter` | `[← Volver] [Continuar →]` al pie del rail izquierdo |
| `SaveChip` | estado de guardado en el header |

---

## 2. Reglas de navegación del wizard

1. El stepper es clickeable **solo hacia atrás** o hacia un paso ya válido.
2. `Continuar →` se habilita cuando el paso actual es válido; deshabilitado debe explicar el motivo vía tooltip.
3. Autoguardado con debounce **800ms** en cada mutación. El botón `Guardar` fuerza el flush inmediato.
4. Al entrar a un proyecto existente, se abre en el **último paso completado + 1**.
5. Nunca se pierde información al retroceder un paso.

### Estados de guardado (`SaveChip`)

| Estado | Texto |
|---|---|
| Guardando | `Guardando…` |
| Guardado | `✓ Guardado 11:06` |
| Error | `⚠ Sin guardar` (rojo, con reintento) |

---

## 3. P0 · Proyectos

**Ruta:** `/proyectos`
**Objetivo:** dar un lugar donde guardar y reabrir proyectos. Es la razón de existir de "Guardar" y del paso 4 reabrible.

```
┌──────────────────────────────────────────────────────────────────────┐
│ 🌿 AgroPlan   Diseño y planificación agrícola        [+ Nuevo proyecto]│
├──────────────────────────────────────────────────────────────────────┤
│  Tus proyectos                                                        │
│  ┌────────────────────┬────────────────────┬────────────────────┐    │
│  │ Mi parcela         │ Parcela Norte      │ + Nuevo proyecto   │    │
│  │ 0,32 ha · 2 cultivos│ 1,10 ha · 3 cultivos│                    │    │
│  │ Riego por goteo    │ Riego por goteo    │  creá tu primer    │    │
│  │ 21/11 11:06  [···] │ 18/11 09:12  [···] │  plano              │    │
│  └────────────────────┴────────────────────┴────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

### Contenido de la tarjeta de proyecto

- Nombre del proyecto.
- Área en hectáreas.
- Cantidad de cultivos.
- Sistema de riego.
- Fecha de última modificación.
- Menú `···`: **Duplicar** · **Exportar** · **Eliminar** (con confirmación).

### Acciones

- `+ Nuevo proyecto` abre un modal de dos campos: **nombre** (requerido, ≤60) y **zona/ubicación** (opcional). Al confirmar, entra al paso 1.

### Estados

- **Vacío (obligatorio):** grilla con una tarjeta punteada `+ Nuevo proyecto` y el texto "Creá tu primer plano".
- **Error de carga:** mensaje con botón `Reintentar`.

### Notas

- **Sin login, sin registro, sin roles.** Un único usuario local.
- El estado vacío es el estado real del jurado si toca "Nuevo proyecto": tiene que verse terminado, no roto.

---

## 4. P1 · Terreno

**Ruta:** `/proyecto/:id/terreno`
**Objetivo:** capturar forma y área de la parcela y el agua disponible. Todo el resto del producto depende de estos números.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🌿 AgroPlan   (1)Terreno ─ 2 Cultivos ─ 3 Sistema ─ 4 Resultado  [PDF][Guardar]│
├──────────────────┬──────────────────────────────────────┬───────────────────┤
│ 📋 DATOS DEL     │ 🟩 Plano 2D — Terreno  [Plano 2D|Medidas] │ 📐 Resumen        │
│    TERRENO       │                                      │                   │
│                  │        N↑                            │ Área    0,32 ha   │
│ Nombre parcela   │        │     60,00 m                 │        3.200 m²   │
│ ┌──────────────┐ │   ┌────┴──────────────────┐         │ Perímetro 172,4 m │
│ │ Mi parcela   │ │   │                       │         │ Lados     4        │
│ └──────────────┘ │40,│      polígono        │20,00 m  │                   │
│                  │00 │                       │         │ ⚠ Validaciones    │
│ Forma            │ m │                       │         │ ✓ Forma cerrada   │
│ ● Rectángulo     │   └───────────────────────┘         │ ✓ Área > 100 m²   │
│ ○ Trapecio       │      30,00 m   ◤42,40 m             │                   │
│ ○ Polígono libre │                                      │ 💧 AGUA DISPONIBLE│
│                  │   ├────┼────┼────┼────┤             │ ● Pozo            │
│ Medidas          │   0   10   20   30   40 m           │ ○ Red             │
│ Largo  60,00 m   │                                      │ ○ Cisterna        │
│ Ancho  30,00 m   │ 🗺 Leyenda                            │ ○ Tanque          │
│ Área   1.800 m²  │ ▭ Borde  ─ Cota  🔵 Vértice          │ Caudal 1,5 m³/h   │
│                  │                                      │                   │
│ Suelo  Franco ▾  │                                      │                   │
│ Pendiente 1 %    │                                      │                   │
│                  │                                      │                   │
│ [← Volver]  [Continuar →]                                 │                   │
└──────────────────┴──────────────────────────────────────┴───────────────────┘
```

### 4.1 Campos (panel izquierdo)

| Campo | Tipo | Regla |
|---|---|---|
| Nombre de parcela | texto | requerido, ≤60 caracteres |
| Forma | radio: Rectángulo / Trapecio / Polígono libre | default `Rectángulo` |
| Largo / Ancho | numérico (m) | requerido, >0, ≤2000 |
| Vértices (polígono libre) | interacción en canvas | mínimo 3, cierra automáticamente |
| Tipo de suelo | select: Franco / Arenoso / Arcilloso / Limoso | requerido — afecta infiltración |
| Pendiente | numérico % | 0–30, default 0 |
| Agua disponible | radio: Pozo / Red / Cisterna / Tanque | requerido |
| Caudal disponible | numérico m³/h | **requerido** — es lo que valida la bomba en el paso 3 |

**Derivados, nunca editables:** Área (fórmula del cordón), Perímetro, Cantidad de lados.

### 4.2 Canvas central

- Polígono cerrado, relleno verde claro, borde verde, vértices con handles arrastrables.
- Líneas de cota con ticks y texto en cada lado (idéntico al estilo de la captura).
- Flecha de norte fija arriba a la izquierda.
- Escala gráfica abajo con marcas cada 10 m.
- Arrastrar un vértice recalcula área, perímetro y cotas **en vivo**. No existe botón "Recalcular".

### 4.3 Estados y errores

| Estado | Comportamiento |
|---|---|
| Vacío | polígono punteado + texto "Elegí una forma para empezar" |
| Autointersección | borde rojo + "El contorno se cruza a sí mismo. Revisá los vértices." |
| Área inválida | `Continuar →` deshabilitado, tooltip "Necesitás un terreno para continuar" |
| Caudal faltante | ⚠ en el panel derecho: "Sin caudal disponible no podemos dimensionar la bomba" |

### 4.4 Salida al paso 2

```json
{
  "geometria": { "vertices": [{"x":0,"y":0}], "cerrado": true },
  "area_m2": 3200,
  "perimetro_m": 172.4,
  "suelo": "franco",
  "pendiente_pct": 1,
  "fuente_agua": "pozo",
  "caudal_disponible_m3h": 1.5
}
```

---

## 5. P2 · Cultivos

**Ruta:** `/proyecto/:id/cultivos`
**Objetivo:** repartir el terreno entre cultivos y definir sus fechas. Es la pantalla donde el usuario **entiende** el producto.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🌿 AgroPlan   ✓Terreno ─ (2)Cultivos ─ 3 Sistema ─ 4 Resultado  [PDF][Guardar]│
├──────────────────┬──────────────────────────────────────┬───────────────────┤
│ 🌱 CULTIVOS      │ 🟩 Plano 2D — Distribución  [Plano 2D|Detalles]  │ 📊 Balance de área│
│                  │                                      │                   │
│ Cultivo          │   ┌───────────────────────────┐       │ ██████████░░ 87 % │
│ ┌──────────────┐ │   │██████ PAPA ███████████████│       │                   │
│ │ 🥔 Papa    ▾ │ │   │██ 2.240 m² ████┌────────┐█│       │ Asignado 2.784 m² │
│ └──────────────┘ │   │████████████████│LECHUGA │█│       │ Disponible 416 m² │
│ Área 2.240 m²    │   │███ 70 % ███████│960 m²  │█│       │ Terreno  3.200 m² │
│ o %   70 %       │   │────────────────┴────────┘█│       │                   │
│                  │   |───────────────────────────|       │ 🗓 Calendario      │
│ Siembra 15/03    │                                      │ Papa   15/03→15/07│
│ Cosecha 15/07    │   [🖌 Dibujar área] [⟳ Repartir %]     │ Lechuga 20/03→25/05│
│ Demanda 2,0      │                                      │ ⚠ Solape: 20/03–  │
│  L/m²/día        │ 🗺 Leyenda                            │   25/05 (2 cult.) │
│                  │ ▨ Papa  ▨ Lechuga  ⬜ Sin asignar     │                   │
│ [+ Agregar cultivo]                                   │ 💧 Demanda hídrica │
│                  │                                      │ Total 6.400 L/día │
│ Cultivos         │                                      │ 2,0 L/m²/día prom.│
│ 1. 🥔 Papa 70% ✕ │                                      │                   │
│ 2. 🥗 Lechuga 30%✕ │                                      │                   │
│                  │                                      │                   │
│ [← Volver]  [Continuar →]                                 │                   │
└──────────────────┴──────────────────────────────────────┴───────────────────┘
```

### 5.1 Comportamiento central: reparto de área

Dos modos de reparto, **mutuamente excluyentes**:

1. **Dibujar área** (principal): el usuario pinta un polígono dentro del terreno. El área se deriva del polígono y se actualiza en vivo.
2. **Repartir %** (atajo): sliders por cultivo; el sistema genera los bloques geométricamente.

Reglas:

- La barra **Balance de área** del panel derecho está siempre visible.
- `Continuar →` se bloquea si `asignado > terreno` o si `cultivos = 0`.

| Estado del balance | Color | Condición |
|---|---|---|
| Correcto | verde | `asignado ≤ terreno` y `disponible ≥ 5%` |
| Ajustado | ámbar | `disponible < 5%` |
| Excedido | rojo | `asignado > terreno` |

### 5.2 Campos por cultivo

| Campo | Tipo | Regla |
|---|---|---|
| Cultivo | select del catálogo mínimo | requerido |
| Área | derivado del dibujo | solo lectura |
| Siembra | date | — |
| Cosecha | date | posterior a siembra |
| Demanda de agua | numérico L/m²/día | default del catálogo, editable **con aviso** |

### 5.3 Catálogo mínimo de cultivos (obligatorio)

Tabla `cultivos` con **5 a 8 filas**, no un módulo:

| Campo | Descripción |
|---|---|
| `nombre` | Papa, Lechuga, Tomate, Maíz, Vid… |
| `icono` | emoji o símbolo |
| `color` | color del bloque en el plano |
| `demanda_agua_l_m2_dia` | consumo diario por m² |
| `demanda_agua_l_planta_dia` | consumo diario por planta |
| `ciclo_dias` | duración del ciclo |

> Sin esta tabla, el resultado "6.400 L/día" del paso 4 no existe. Son 8 filas de SQL.

### 5.4 Panel derecho

- **Balance de área** (barra + asignado / disponible / terreno).
- **Calendario** por cultivo con **detección de solape** entre ciclos.
- **Demanda hídrica total** en L/día y promedio L/m²/día.
- Advertencia si `demanda_total > caudal_disponible × 24`: "La demanda diaria supera el agua que podés extraer en un día."

### 5.5 Errores

| Caso | Mensaje |
|---|---|
| Área excedida | "Asignaste 3.400 m² sobre un terreno de 3.200 m². Te sobran 200 m²." |
| Cultivo sin área | "El cultivo Papa no tiene área asignada." |
| Fechas invertidas | "La cosecha debe ser posterior a la siembra." |
| Sin cultivos | `Continuar →` deshabilitado, "Agregá al menos un cultivo para continuar" |

### 5.6 Salida al paso 3

```json
{
  "cultivos": [
    { "cultivo_id": "papa", "area_m2": 2240, "siembra": "2026-03-15", "cosecha": "2026-07-15", "demanda_l_m2_dia": 2.0 }
  ],
  "area_asignada_m2": 3200,
  "demanda_total_l_dia": 6400
}
```

---

## 6. P3 · Sistema

**Ruta:** `/proyecto/:id/sistema`
**Objetivo:** definir fuente, tanque, bomba y emisores, y **generar la red de goteo**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🌿 AgroPlan   ✓Terreno ─ ✓Cultivos ─ (3)Sistema ─ 4 Resultado  [PDF][Guardar]│
├──────────────────┬──────────────────────────────────────┬───────────────────┤
│ 💧 SISTEMA DE    │ 🟩 Plano 2D — Red de goteo  [Plano 2D|Detalles]  │ ⚙️ Preview técnico│
│    RIEGO         │                                      │                   │
│ ● Riego por goteo│   ⛁ Tanque 5.000 L                   │ Caudal/sector     │
│ ○ Aspersión      │    ⚙ Bomba 1 HP                      │   0,9 m³/h  ✓     │
│ ○ Inundación     │     │                                │ Caudal total      │
│                  │   ┌─┴───────────────────────┐        │   1,8 m³/h        │
│ Fuente  Pozo   ▾ │   │ ═══ principal Ø32 ══╗   │        │ Presión req.      │
│ Tanque  5000 L   │   │ ┌┄┄┐┄┄┐┄┄┐┄┄┐┄┄┐┄┄┐ │        │   1,3 bar   ✓     │
│ Bomba   1 HP   ▾ │   │ ├┄┄┤┄┄┤┄┄┤┄┄┤┄┄┤┄┄┤ ║        │ Tiempo de riego   │
│                  │   │ └┄┄┘┄┄┘┄┄┘┄┄┘┄┄┘┄┄┘ ✕       │   3 h 33 min      │
│ ── Emisores ──   │   │      ═══ Ø32 ═══╗   ✕        │                   │
│ Gotero  2,0 L/h  │   └──────────────────╜           │ ⚠️ Advertencias    │
│ Sep. goteros 0,2m│                                  │ ⚠ Autonomía tanque│
│ Sep. laterales 5m│   [⚡ Generar red] [✋ Editar]     │   0,8 días (<1)   │
│                  │                                  │ ✓ Presión en rango│
│ ── Sectores ──   │ 🗺 Leyenda                        │ ✓ Caudal ≤ bomba  │
│ Sectores 2  [⚙]  │ ═ Principal  ┄ Lateral  🔵 Gotero │                   │
│                  │ ✕ Válvula  ⛁ Tanque  ⚙ Bomba      │ 💰 Cómputo rápido │
│                  │                                  │ Tubería    498 m  │
│ [← Volver]  [Continuar →]                             │ Goteros  2.100 u  │
│                  │                                  │ Válvulas     4 u  │
└──────────────────┴──────────────────────────────────────┴───────────────────┘
```

### 6.1 Decisión de diseño crítica

> **La red no se dibuja a mano: se genera.**

La captura muestra una grilla perfecta de laterales: eso es un algoritmo determinístico, no un editor libre. Los inputs reales son los **parámetros de generación**:

`separación entre laterales` + `separación entre goteros` + `orientación` + `punto de conexión` + `n sectores` → **red**

Después, `Editar` permite mover el cabezal o corregir un lateral puntual. Construir un editor libre desde cero en un día no llega a tiempo ni de casualidad.

Los parámetros de generación deben persistirse junto con la red para poder regenerarla sin perder ajustes manuales.

### 6.2 Campos (panel izquierdo)

| Campo | Tipo | Regla |
|---|---|---|
| Sistema | radio: Goteo / Aspersión / Inundación | MVP: solo **Goteo** habilitado; el resto "Próximamente" |
| Fuente | select: Pozo / Red / Cisterna / Tanque | debe ser compatible con el paso 1 |
| Capacidad de tanque | numérico L | >0 |
| Bomba | select HP: 0,5 / 1 / 1,5 / 2 | — |
| Caudal del gotero | select: 2 / 4 / 8 L/h | default 2 |
| Separación goteros | numérico m | 0,2–1,0 |
| Separación laterales | numérico m | 0,5–10 |
| Sectores | numérico 1–8 + botón ⚙ | 1–8, abre el modal de sectores |

### 6.3 Cálculos deterministas

Se muestran, no se inventan:

| Métrica | Fórmula |
|---|---|
| Goteros | `área / (sep_laterales × sep_goteros)` |
| Cantidad de laterales | `largo / sep_laterales` |
| Longitud de lateral | `ancho` |
| Caudal por sector | `goteros_del_sector × q_gotero` |
| Caudal total | `caudal_sector` (riego secuencial) |
| Presión requerida | `f(longitud, diámetro, caudal)` — **estimación preliminar** |
| Tiempo de riego | `demanda_día / caudal_sector` |
| Autonomía del tanque | `capacidad / consumo_diario` |

Toda salida hidráulica se etiqueta como **estimación preliminar**.

### 6.4 Panel derecho: Preview técnico

Se calcula **en vivo, antes de presionar "Generar red"**. Es lo que convierte esto en herramienta y no en un dibujito. Nunca oculta el rojo.

| Condición | Nivel | Mensaje |
|---|---|---|
| `caudal_total > caudal_disponible` | ⚠ | "El caudal requerido supera el agua disponible (1,8 > 1,5 m³/h). Sumá un sector." |
| `autonomía < 1 día` | ⚠ | "El tanque se vacía en 0,8 días. Necesitás 6.400 L o recarga diaria." |
| presión fuera de 1–1,5 bar | ⚠ | "La presión estimada (0,7 bar) está por debajo del rango recomendado." |
| presión en rango | ✓ | "Presión en rango." |
| `caudal_total ≤ bomba` | ✓ | "Caudal admisible por la bomba." |

Además: **cómputo rápido** (metros de tubería, goteros, válvulas) como anticipo del paso 4.

### 6.5 Errores

| Caso | Mensaje |
|---|---|
| Separación inválida | "La separación entre goteros debe estar entre 0,2 y 1,0 m." |
| Red sin generar | `Continuar →` deshabilitado, "Generá la red de goteo para ver el resultado" |
| Bomba insuficiente | ⚠ bloqueante visual, pero se permite continuar con advertencia explícita |

### 6.6 Salida al paso 4

```json
{
  "sistema": "goteo",
  "fuente": "pozo",
  "tanque_l": 5000,
  "bomba_hp": 1,
  "emisor": { "tipo": "gotero", "caudal_lh": 2.0, "sep_m": 0.2 },
  "laterales_sep_m": 5,
  "sectores": [{ "n": 1, "area_m2": 2240, "goteros": 1400, "caudal_m3h": 0.9 }],
  "parametros_generacion": { "orientacion": "E-O", "conexion": { "x": 0, "y": 0 } },
  "red": { "nodos": [], "tramos": [] },
  "computo": { "tuberia_m": 498, "goteros_u": 2100, "valvulas_u": 4 }
}
```

---

## 7. P3.1 · Modal "Configurar sectores"

**Se abre desde:** botón ⚙ junto al campo `Sectores` del paso 3.
**Por qué es obligatorio:** con 2 o más sectores el cálculo global no cierra solo. Hay que decidir qué área va a cada sector y en qué orden. Sin este modal, el número "1,8 m³/h" del paso 4 no se puede justificar.

```
┌─────────────────────── Configurar sectores ───────────────────────┐
│ 2 sectores · caudal 0,9 m³/h c/u                                  │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ ● Sector 1   Papa (2.240 m²)      1.400 goteros   0,9 m³/h  │  │
│ │ ● Sector 2   Lechuga (960 m²)       700 goteros   0,9 m³/h  │  │
│ └──────────────────────────────────────────────────────────────┘  │
│ Secuencia: [S1 → S2]  ⏱ Tiempo total 7 h 06 min                   │
│ [Cancelar]                                    [Aplicar y generar]  │
└───────────────────────────────────────────────────────────────────┘
```

### Contenido

- Una fila por sector: número, cultivo/área asignada, cantidad de goteros, caudal.
- Asignación de área a cada sector (por cultivo o por superficie).
- Orden de la secuencia.
- Tiempo total de riego de la secuencia completa.

### Acciones

- `Cancelar`: cierra sin cambios.
- `Aplicar y generar`: persiste la configuración y regenera la red del paso 3.

### Validaciones

| Caso | Mensaje |
|---|---|
| Área de sectores ≠ área total | "La suma de los sectores (3.100 m²) no cubre el área asignada (3.200 m²)." |
| Sector sin emisores | "El sector 2 no tiene emisores asignados." |
| Caudal por sector > disponible | "El sector 1 requiere 2,1 m³/h y solo tenés 1,5 m³/h disponibles." |

---

## 8. Modales compartidos

### 8.1 Guardar

No abre ninguna pantalla. Es un `SaveChip` en el header con autoguardado (ver §2). El botón `Guardar` fuerza el flush.

### 8.2 Exportar PDF

```
┌──────────── Exportar PDF ─────────────┐
│ ☑ Plano 2D con leyenda y cotas        │
│ ☑ Cómputo de materiales               │
│ ☑ Requerimiento de agua               │
│ ☑ Calendario de cultivos              │
│ ☐ Recomendaciones                     │
│                        [Cancelar] [⤓]  │
└───────────────────────────────────────┘
```

- El PDF se genera **en el backend** desde el grafo, no en el cliente.
- Toda página lleva marca de agua: **"Estimación preliminar — no apta para ejecución"**.

---

## 9. Flujo de datos entre pantallas

```
Terreno ──geometría + agua──▶ Cultivos ──áreas + demanda──▶ Sistema ──red + cómputo──▶ Resultado
   │                              │                            │
   └──────────── todo se deriva de la geometría ───────────────┘
```

**Riesgo principal del hackathon:** si el estado del proyecto no es **uno solo** y compartido entre los cuatro pasos, el paso 4 va a mostrar números que no coinciden con lo que el usuario cargó — y eso es exactamente lo que se rompe en la demo, en vivo, frente al jurado.

### Contrato mínimo compartido

```ts
type Proyecto = {
  id: string
  nombre: string
  terreno: Terreno
  cultivos: CultivoAsignado[]
  sistema: ConfiguracionSistema
  red: Red
  meta: { creado: string; modificado: string; version: number }
}
```

Tipado estricto (discriminated unions para nodos y tramos). Nada de `properties_json` sin esquema.

---

## 10. Checklist de decisiones a cerrar antes de escribir código

1. ¿Cultivos se reparte **dibujando** o solo por **porcentaje**? Dibujar vende mucho más, pero cuesta el doble.
2. ¿La red de goteo se **genera** o se dibuja a mano? Recomendación: generar.
3. ¿Aspersión e inundación quedan como "Próximamente" o hay que mostrar algo funcional?
4. ¿Entra cálculo hidráulico o solo topología + cómputo? Recomendación: solo topología + cómputo, con la presión etiquetada como estimación.
5. ¿Una sola fuente de verdad para longitud y área? **Obligatorio que sí.**

---

## 11. Resumen de entregables

| # | Pantalla | Complejidad | Notas |
|---|---|---|---|
| 0 | Proyectos | baja | Estado vacío obligatorio |
| 1 | Terreno | media | Canvas de polígono + cotas |
| 2 | Cultivos | media-alta | Dibujo de áreas + balance |
| 3 | Sistema | alta | Generación de red + preview técnico |
| 3.1 | Sectores (modal) | baja | Obligatorio para que el cálculo cierre |
| 4 | Resultado | — | Ya existe |

---

*Documento de definición visual. No incluye implementación. Fórmulas, reglas, catálogos y precios deben validarse con profesionales competentes antes de usar el sistema para ejecutar instalaciones reales.*
