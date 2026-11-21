---
name: AgroPlan Design System
colors:
  surface: '#eaffea'
  surface-dim: '#a9e9b6'
  surface-bright: '#eaffea'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#d1ffd8'
  surface-container: '#bcfdc9'
  surface-container-high: '#b7f7c3'
  surface-container-highest: '#b1f2be'
  on-surface: '#00210d'
  on-surface-variant: '#404940'
  inverse-surface: '#00391a'
  inverse-on-surface: '#c3ffce'
  outline: '#707a6f'
  outline-variant: '#bfc9bd'
  surface-tint: '#1f6c3a'
  primary: '#004c22'
  on-primary: '#ffffff'
  primary-container: '#166534'
  on-primary-container: '#93e0a2'
  inverse-primary: '#8bd79b'
  secondary: '#1b6d24'
  on-secondary: '#ffffff'
  secondary-container: '#a0f399'
  on-secondary-container: '#217128'
  tertiary: '#653400'
  on-tertiary: '#ffffff'
  tertiary-container: '#874700'
  on-tertiary-container: '#ffc292'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#a6f4b5'
  primary-fixed-dim: '#8bd79b'
  on-primary-fixed: '#00210b'
  on-primary-fixed-variant: '#005226'
  secondary-fixed: '#a3f69c'
  secondary-fixed-dim: '#88d982'
  on-secondary-fixed: '#002204'
  on-secondary-fixed-variant: '#005312'
  tertiary-fixed: '#ffdcc3'
  tertiary-fixed-dim: '#ffb77d'
  on-tertiary-fixed: '#2f1500'
  on-tertiary-fixed-variant: '#6e3900'
  background: '#eaffea'
  on-background: '#00210d'
  surface-variant: '#b1f2be'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 18px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.02em
  tabular-data:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 0.75rem
  gutter-desktop: 1rem
  margin: 1rem
  margin-desktop: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

The design system is structured for precision agriculture, land planning, and agronomic management tools. The visual aesthetic pairs the rigorous utilitarian clarity of technical CAD/GIS blueprints with the approachability of clean, modern enterprise software.

### Tone & Personality
- **Reliable & Scientific:** Grounded in real-world measurements, hydraulic standards, and biological schedules.
- **Clear & High-Legibility:** Designed for outdoor sunlight readability, dense metric dashboards, and high-contrast data visualization.
- **Systematic & Modular:** Clean white cards with subtle hairline borders, allowing complex spatial canvas layouts and structured data tables to coexist harmoniously.

### Visual Style
A blend of **Modern Clean Functionalism** and **Technical Agronomic Precision**:
- Surfaces remain predominantly clean white `#FFFFFF` against a crisp, organic tinted background `#F6F8F6`.
- Structural borders use calm, muted sage tones (`#E2E8E2`) rather than harsh cold grays.
- Vibrant, calibrated shades of forest and emerald green anchor primary actions, active navigational states, and success indicators, while warm ambers are reserved for agronomic recommendations and technical alerts.

## Colors

The palette directly models agricultural landscapes: healthy foliage, fresh water infrastructure, and rich soils, calibrated for high-density information display.

### Primary & Functional Palette
- **Primary Deep Green (`#14532D` / `--verde-900`):** Used for top-level headers, primary brand presence, key navigation buttons, and high-emphasis labels.
- **Secondary Agronomic Emerald (`#166534` / `--verde-700`):** Primary interactive actions, selected state pills, success badges, and main button containers.
- **Vibrant Accent Green (`#2E7D32` / `--verde-600`):** Interactive toggle states, active canvas vectors, edit buttons, and metric icons.
- **Subtle Tint Green (`#E8F5E9` / `--verde-100`):** Background fill for selected rows, active chips, badge surfaces, and low-priority highlight cards.

### Neutral & Surface Hierarchy
- **Canvas Base (`#F6F8F6` / `--fondo`):** Soft, non-glare off-white background ensuring comfortable reading over extended operational periods.
- **Card & Modal Surface (`#FFFFFF`):** Pure white container surfaces that provide contrast against the tinted base canvas.
- **Hairline Border (`#E2E8E2` / `--borde`):** Ultra-crisp, low-contrast structural boundaries isolating modules without adding visual clutter.
- **Text Primary (`#111827`):** High legibility dark slate for numeric values, data tables, and body copy.
- **Text Secondary (`#4B5563`):** Medium contrast for unit qualifiers (e.g., `m²`, `L/h`, `ha`), field labels, and disabled states.

### Status & Feedback
- **Recommendation / Agronomic Tip:** Background `#FFF8E1`, Border `#FDE68A`, Icon & Accent `#D97706` / `#F59E0B`.
- **System Error / Warning Limit:** Border `#FCA5A5`, Accent `#DC2626`.
- **Hydraulic / Water Indicators:** Cyan/Azure accents `#0284C7` and `#0369A1` dedicated strictly to irrigation lines, pumps, and water volume.

## Typography

The typography uses **Inter** across all UI layers to ensure maximum optical clarity when scanning dense numeric tables, engineering units, and CAD blueprint measurements.

### Type Hierarchy Principles
- **Display & Section Headers:** Uses semibold and bold weights with tighter tracking (`-0.02em` to `-0.01em`) to create definitive anchor zones across panels.
- **Base Body (`13px`):** Chosen specifically to optimize spatial density for multi-column agronomic cards, allowing detailed technical descriptors without requiring vertical scrolling.
- **Numeric & Technical Data:** Applied via `tabular-data` with `font-feature-settings: 'tnum' on, 'cv05' on` to keep decimal points, metric values (`0.32 ha`, `60.00 m`), and bills of materials perfectly aligned.

## Layout & Spacing

The layout follows a modular 3-column dashboard model tailored for spatial planning applications:
- **Left Inspector (240px - 280px):** Project metadata, crop distributions, and hydraulic configuration summary.
- **Central Canvas (Flexible 1fr):** Dynamic 2D interactive viewport showcasing parcel geometry, irrigation layouts, dimensions, and operational zones.
- **Right Analytics & Bill of Materials (300px - 340px):** Project outputs, material computations, water consumption estimations, agronomic calendar, and warning callouts.

### Breakpoints & Reflow
- **Desktop (>= 1280px):** Full 3-column layout with pinned sidebars and expand-to-fit canvas viewport.
- **Tablet (768px - 1279px):** Inspector and Analytics collapse into tabbed side panels or a sliding drawer, prioritizing the canvas area.
- **Mobile (< 768px):** Stacks hierarchically: Step wizard navigation, primary canvas preview, followed by stacked accordion cards.

### Spacing Rhythm
Standard structural rhythm strictly adheres to multiples of 4px. Card padding uses `space-md` (12px) or `space-lg` (16px) to maximize data density while preserving visual breathing room.

## Elevation & Depth

The design system relies on flat, clinical clarity with ultra-subtle dimensional separation, avoiding heavy dropshadows that could conflict with vector map lines and technical drawings.

### Depth Stratification
- **Ground Floor (Base Canvas):** Tinted natural background (`#F6F8F6`).
- **Level 1 (Card & Module Containers):** Pure white background (`#FFFFFF`) with a 1px solid hairline border (`#E2E8E2`) and an ambient micro-shadow: `0 1px 3px rgba(0, 0, 0, 0.05)`.
- **Level 2 (Canvas Overlays & Controls):** Segmented view controls, legend bars, and floating measurement pills sit over the 2D map with a focused shadow: `0 2px 6px rgba(0, 0, 0, 0.08)`.
- **Level 3 (Modals & Flyouts):** Dialogs and dropdown pickers with `0 10px 25px -5px rgba(20, 83, 45, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.04)`.

## Shapes

The interface balances sharp technical precision with approachable organic soft curves:

- **Cards, Panels & Viewport Containers:** `12px` border radius (`rounded-lg`), providing a clean frame around dense lists and 2D canvas boards.
- **Interactive Controls, Form Inputs & Table Rows:** `8px` border radius (`rounded-md`), offering reliable touch and click targets.
- **Step Wizard Indicators, Badges & Action Buttons:** Full pill geometry (`rounded-full` / `9999px`) used for wizard progress steps (e.g., `1 Terreno`, `2 Cultivos`, `4 Resultado`), status chips, and primary utility actions (`Exportar PDF`, `Guardar`).

## Components

### Buttons
- **Primary (`.btn-primary`):** Solid `#166534` background, white text, 8px or pill radius, hover `#14532D`.
- **Secondary Action (`.btn-secondary`):** `#2E7D32` background, white text, crisp hover state with a slight brightness boost.
- **Outline / Utility (`.btn-outline`):** White surface, `#E2E8E2` border, `#166534` text and icon. On hover, background shifts to `#E8F5E9` and border transitions to `#166534`.

### Step Wizard (Progress Stepper)
- Horizontal floating bar container in `#FFFFFF` with `#E2E8E2` border and `9999px` radius.
- Inactive steps: Neutral outline or light gray circle with dark slate typography.
- Active / Completed step: Filled emerald green `#166534` circle with crisp bold numbering, paired with `#14532D` semibold label text.

### Cards & Module Headers
- White solid surface, 12px radius, hairline border `#E2E8E2`.
- Section header row: Left-aligned icon (20px) tinted in `#166534` or `#2E7D32` paired with `headline-sm` (15px semibold).
- Top banner cards for alerts / tips use `#FFF8E1` surface, `#FDE68A` border, and warm amber light bulb icon.

### Data Tables (Cómputo de Materiales & Calendario)
- Crisp border-collapse table layout with `#F6F8F6` header row and 11px uppercase/semibold headers (`#4B5563`).
- Data rows feature 13px tabular numbers, cell borders in `#E2E8E2`, and alternate row hover state `#F9FAF9`.
- Key status icons inline (e.g., crop icons, checkmarks, pipe cross-sections).

### Canvas Legend & Overlay Panels
- Semi-translucent white surface (`rgba(255, 255, 255, 0.95)`) with backdrop blur of 4px.
- Key-value indicator lines displaying real-world CAD symbology (main pipe, lateral drip line, dripper emitter, valve, and living barrier tree markers).