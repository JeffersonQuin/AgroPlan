export type ParcelShape = 'rectangulo' | 'trapecio' | 'libre';

/** Código de suelo: los del catálogo del backend, que crece con migraciones. */
export type SoilType = string;

export type WaterSource = 'pozo' | 'tanque' | 'red' | 'cisterna' | 'pila';

export interface TerrainDimensions {
  /** Largo superior, in metres. */
  topM: number;
  /** Base inferior, in metres. */
  bottomM: number;
  /** Lateral izquierdo (alto), in metres. */
  leftM: number;
  /** Lateral derecho, in metres. */
  rightM: number;
}

export interface TerrainState {
  name: string;
  shape: ParcelShape;
  dimensions: TerrainDimensions;
  soil: SoilType;
  slopePct: number;
  /** ``false`` = el usuario no la informó: se usa una pendiente asumida. */
  pendienteConocida: boolean;
  waterSource: WaterSource;
  /** Caudal disponible (aforo), m³/h. ``null`` = no lo informó: lo asume el sistema. */
  flowM3h: number | null;
  /** Profundidad del nivel dinámico, m. ``null`` = no informada. */
  staticLevelM: number | null;
}

export interface TerrainMetrics {
  areaM2: number;
  perimeterM: number;
  diagonalM: number;
}

export interface ShapeOption {
  value: ParcelShape;
  label: string;
}

export interface SoilOption {
  value: SoilType;
  label: string;
  infiltration: string;
}

export interface WaterSourceOption {
  value: WaterSource;
  label: string;
}

export const SHAPE_OPTIONS: readonly ShapeOption[] = [
  { value: 'rectangulo', label: 'Rectángulo' },
  { value: 'trapecio', label: 'Trapecio' },
  { value: 'libre', label: 'Polígono libre' },
];

export const SOIL_OPTIONS: readonly SoilOption[] = [
  {
    value: 'franco',
    label: 'Franco (Ideal, retención equilibrada)',
    infiltration: '15-25 mm/h',
  },
  {
    value: 'arenoso',
    label: 'Arenoso (Infiltración rápida > 30 mm/h)',
    infiltration: '> 30 mm/h',
  },
  {
    value: 'arcilloso',
    label: 'Arcilloso (Infiltración lenta < 8 mm/h)',
    infiltration: '< 8 mm/h',
  },
  {
    value: 'limoso',
    label: 'Limoso (Medio-fino, riesgo compactación)',
    infiltration: '8-15 mm/h',
  },
];

export const WATER_SOURCE_OPTIONS: readonly WaterSourceOption[] = [
  { value: 'pozo', label: 'Pozo' },
  { value: 'tanque', label: 'Tanque' },
  { value: 'red', label: 'Red presión' },
  { value: 'cisterna', label: 'Cisterna' },
  { value: 'pila', label: 'Pila' },
];

/**
 * Pendiente que asume el sistema cuando el usuario no la informa: un terreno
 * agrícola plano suele estar entre 0 y 2%, y 1% deja desagüe sin complicar el riego.
 */
export const PENDIENTE_ASUMIDA_PCT = 1;

export const INITIAL_TERRAIN: TerrainState = {
  name: 'Mi parcela',
  shape: 'trapecio',
  dimensions: { topM: 60, bottomM: 30, leftM: 40, rightM: 20 },
  soil: 'franco',
  slopePct: PENDIENTE_ASUMIDA_PCT,
  pendienteConocida: false,
  waterSource: 'pozo',
  // Vacíos a propósito: el backend asigna caudal y el usuario no tiene por qué
  // saber el aforo de su pozo para usar el paso 1.
  flowM3h: null,
  staticLevelM: null,
};

/* -------------------------------------------------------------------------- */
/* Backend contract (FastAPI)                                                  */
/* -------------------------------------------------------------------------- */

export type FormaTerrenoApi = 'rectangulo' | 'trapecio' | 'poligono';

export type FuenteAguaApi = 'pila' | 'pozo' | 'red' | 'cisterna' | 'tanque';

export type OrigenCaudalApi = 'cliente' | 'asumido';

export interface VerticeApi {
  x: number;
  y: number;
}

export interface AdvertenciaApi {
  codigo: string;
  mensaje: string;
  bloqueante: boolean;
  campo: string | null;
}

/** `GET`/`PUT`/`PATCH /proyectos/{id}/terreno`. */
export interface TerrenoApi {
  id: string;
  nombre_parcela: string;
  forma: FormaTerrenoApi;
  geometria: { vertices: VerticeApi[]; cerrado: boolean; unidad: string; eje_y: string };
  area_m2: number;
  perimetro_m: number;
  lados: number;
  lados_m: { desde: number; hasta: number; longitud_m: number }[];
  suelo_codigo: string;
  pendiente_pct: number;
  fuente_agua: FuenteAguaApi;
  caudal_disponible_m3h: number | null;
  caudal_efectivo_m3h: number;
  caudal_origen: OrigenCaudalApi;
  caudal_sugerido_m3h: number | null;
  profundidad_nivel_dinamico_m: number | null;
  alertas: AdvertenciaApi[];
}

/** Payload accepted by `PUT` (all) and `PATCH` (all optional). */
export interface GuardarTerrenoApi {
  nombre_parcela: string;
  forma: FormaTerrenoApi;
  vertices: VerticeApi[];
  suelo_codigo: string;
  pendiente_pct: number;
  fuente_agua: FuenteAguaApi;
  /** ``null`` = no informado: el backend asigna uno según la fuente. */
  caudal_disponible_m3h: number | null;
  profundidad_nivel_dinamico_m: number | null;
}

export interface SueloApi {
  codigo: string;
  nombre: string;
  infiltracion_mm_h: number;
  retencion_agua_mm_m: number | null;
}

/** The two shape vocabularies: the mockup says "libre", the backend "poligono". */
export const FORMA_API: Record<ParcelShape, FormaTerrenoApi> = {
  rectangulo: 'rectangulo',
  trapecio: 'trapecio',
  libre: 'poligono',
};

export type EstadoTerreno = 'inicial' | 'cargando' | 'listo' | 'guardando' | 'guardado' | 'error';
