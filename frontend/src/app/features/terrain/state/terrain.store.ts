import { Service, computed, signal } from '@angular/core';
import {
  INITIAL_TERRAIN,
  ParcelShape,
  SHAPE_OPTIONS,
  SOIL_OPTIONS,
  SoilType,
  TerrainDimensions,
  TerrainMetrics,
  TerrainState,
  WaterSource,
} from '../models/terrain.model';
import {
  calculateDesnivel,
  calculateMetrics,
  REFERENCE_DIMENSIONS,
  REFERENCE_METRICS,
} from '../utils/terrain-geometry';

const SHAPE_LABELS: Record<ParcelShape, string> = {
  rectangulo: '4 lados (rectángulo)',
  trapecio: '4 lados (trapecio)',
  libre: 'polígono libre',
};

/**
 * Terrain step state: the parcel identity, its cotas, the soil, the slope and
 * the water source, plus every derived figure the two side rails show.
 *
 * Scope: presentation only. Nothing is persisted or sent to the backend yet.
 */
@Service()
export class TerrainStore {
  private readonly _state = signal<TerrainState>({
    ...INITIAL_TERRAIN,
    dimensions: { ...INITIAL_TERRAIN.dimensions },
  });

  readonly state = this._state.asReadonly();

  readonly name = computed(() => this._state().name);
  readonly shape = computed(() => this._state().shape);
  readonly dimensions = computed(() => this._state().dimensions);
  readonly soil = computed(() => this._state().soil);
  readonly slopePct = computed(() => this._state().slopePct);
  readonly waterSource = computed(() => this._state().waterSource);
  readonly flowM3h = computed(() => this._state().flowM3h);
  readonly staticLevelM = computed(() => this._state().staticLevelM);

  /** Reference metrics until a cota changes, then the real geometry. */
  readonly metrics = computed<TerrainMetrics>(() => {
    const dimensions = this._state().dimensions;
    return isReference(dimensions) ? REFERENCE_METRICS : calculateMetrics(dimensions);
  });

  readonly desnivelM = computed(() =>
    calculateDesnivel(this._state().dimensions.topM, this._state().slopePct),
  );

  readonly areaHaLabel = computed(() => `${(this.metrics().areaM2 / 10000).toFixed(2)} ha`);
  readonly areaSqMLabel = computed(() => `(${formatThousands(this.metrics().areaM2)} m²)`);
  readonly perimeterLabel = computed(() => `${this.metrics().perimeterM.toFixed(1)} m`);
  readonly diagonalLabel = computed(() => `${this.metrics().diagonalM.toFixed(2)} m`);
  readonly verticesLabel = computed(() => SHAPE_LABELS[this._state().shape]);
  readonly slopeLabel = computed(() => `${this._state().slopePct.toFixed(1)} %`);
  readonly desnivelLabel = computed(
    () => `${this.desnivelM().toFixed(2)} m (${this._state().slopePct}% pend.)`,
  );
  readonly infiltrationLabel = computed(() => {
    const option = SOIL_OPTIONS.find((soil) => soil.value === this._state().soil);
    return option ? `Infiltración: ${option.infiltration}` : '';
  });

  setName(name: string): void {
    this._state.update((state) => ({ ...state, name }));
  }

  setShape(shape: ParcelShape): void {
    this._state.update((state) => ({ ...state, shape }));
  }

  setDimension(key: keyof TerrainDimensions, value: number): void {
    this._state.update((state) => ({
      ...state,
      dimensions: { ...state.dimensions, [key]: Number.isFinite(value) ? value : 0 },
    }));
  }

  setSoil(soil: SoilType): void {
    this._state.update((state) => ({ ...state, soil }));
  }

  setSlope(slopePct: number): void {
    this._state.update((state) => ({ ...state, slopePct }));
  }

  setWaterSource(waterSource: WaterSource): void {
    this._state.update((state) => ({ ...state, waterSource }));
  }

  setFlow(flowM3h: number): void {
    this._state.update((state) => ({ ...state, flowM3h }));
  }

  setStaticLevel(staticLevelM: number): void {
    this._state.update((state) => ({ ...state, staticLevelM }));
  }

  shapeLabel(shape: ParcelShape): string {
    return SHAPE_OPTIONS.find((option) => option.value === shape)?.label ?? '';
  }
}

function isReference(dimensions: TerrainDimensions): boolean {
  return (
    dimensions.topM === REFERENCE_DIMENSIONS.topM &&
    dimensions.bottomM === REFERENCE_DIMENSIONS.bottomM &&
    dimensions.leftM === REFERENCE_DIMENSIONS.leftM &&
    dimensions.rightM === REFERENCE_DIMENSIONS.rightM
  );
}

function formatThousands(value: number): string {
  return Math.round(value)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}
