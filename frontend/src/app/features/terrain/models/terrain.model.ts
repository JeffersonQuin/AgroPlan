export type ParcelShape = 'rectangulo' | 'trapecio' | 'libre';

export type SoilType = 'franco' | 'arenoso' | 'arcilloso' | 'limoso';

export type WaterSource = 'pozo' | 'tanque' | 'red' | 'cisterna';

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
  waterSource: WaterSource;
  /** Caudal disponible (aforo), m³/h. */
  flowM3h: number;
  /** Profundidad del nivel dinámico, m. */
  staticLevelM: number;
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
];

export const INITIAL_TERRAIN: TerrainState = {
  name: 'Mi parcela',
  shape: 'trapecio',
  dimensions: { topM: 60, bottomM: 30, leftM: 40, rightM: 20 },
  soil: 'franco',
  slopePct: 1,
  waterSource: 'pozo',
  flowM3h: 1.8,
  staticLevelM: 18,
};
