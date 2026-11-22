import { HttpErrorResponse } from '@angular/common/http';
import { Service, computed, inject, signal } from '@angular/core';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ProjectsApi } from '../../projects/projects.api';
import { mensajeDeError } from '../../projects/state/projects.store';
import {
  AdvertenciaApi,
  EstadoTerreno,
  FORMA_API,
  INITIAL_TERRAIN,
  SHAPE_OPTIONS,
  SOIL_OPTIONS,
  SoilType,
  SueloApi,
  TerrainDimensions,
  TerrainMetrics,
  TerrainState,
  TerrenoApi,
  WaterSource,
} from '../models/terrain.model';
import { TerrainApi } from '../terrain.api';
import {
  areaPoligono,
  calculateDesnivel,
  calculateMetrics,
  fromVertices,
  seAutoIntersecta,
  toVertices,
} from '../utils/terrain-geometry';

export interface Validacion {
  ok: boolean;
  texto: string;
}

const AREA_MINIMA_M2 = 100;
const PENDIENTE_MAXIMA_PCT = 10;

const SHAPE_LABELS: Record<string, string> = {
  rectangulo: '4 lados (rectángulo)',
  trapecio: '4 lados (trapecio)',
  libre: 'polígono libre',
};

/**
 * Terrain step state, backed by the API.
 *
 * The four cotas, the soil, the slope and the water source are the input; the
 * backend derives area, perimeter, side count and the effective flow rate from the
 * same vertices, and those numbers win over the local preview once the terrain is
 * saved.
 */
@Service()
export class TerrainStore {
  private readonly api = inject(TerrainApi);
  private readonly projectsApi = inject(ProjectsApi);

  private readonly _state = signal<TerrainState>({
    ...INITIAL_TERRAIN,
    dimensions: { ...INITIAL_TERRAIN.dimensions },
  });
  private readonly _nombreEditado = signal(false);
  private readonly _proyectoId = signal<string | null>(null);
  private readonly _nombreProyecto = signal('');
  private readonly _guardado = signal<TerrenoApi | null>(null);
  private readonly _estado = signal<EstadoTerreno>('inicial');
  private readonly _error = signal<string | null>(null);
  private readonly _suelos = signal<SueloApi[]>([]);

  readonly state = this._state.asReadonly();
  readonly estado = this._estado.asReadonly();
  readonly error = this._error.asReadonly();
  readonly suelos = this._suelos.asReadonly();
  readonly guardado = this._guardado.asReadonly();

  readonly proyectoId = this._proyectoId.asReadonly();
  readonly nombreProyecto = computed(() => this._nombreProyecto() || 'Proyecto sin nombre');

  readonly name = computed(() => this._state().name);
  readonly shape = computed(() => this._state().shape);
  readonly dimensions = computed(() => this._state().dimensions);
  readonly soil = computed(() => this._state().soil);
  readonly slopePct = computed(() => this._state().slopePct);
  readonly waterSource = computed(() => this._state().waterSource);
  readonly flowM3h = computed(() => this._state().flowM3h);
  readonly staticLevelM = computed(() => this._state().staticLevelM);

  /** Live preview from the cotas; the saved terrain overrides it. */
  readonly metrics = computed<TerrainMetrics>(() =>
    calculateMetrics(this._state().dimensions, this._state().shape),
  );

  /** The polygon that is drawn and, on save, sent to the backend. */
  readonly vertices = computed(() =>
    toVertices(this._state().dimensions, this._state().shape),
  );

  /** Cotas the current shape actually uses: a rectangle ignores base and right side. */
  readonly cotasVisibles = computed(() => {
    const shape = this._state().shape;
    return {
      topM: shape === 'rectangulo' ? 'Largo' : 'Largo Superior',
      bottomM: shape !== 'rectangulo',
      leftM: shape === 'rectangulo' ? 'Alto' : 'Lateral Izq. (Alto)',
      rightM: shape !== 'rectangulo',
    };
  });

  readonly desnivelM = computed(() =>
    calculateDesnivel(this._state().dimensions.topM, this._state().slopePct),
  );

  /** Numbers the backend derived, or ``null`` while the terrain is unsaved. */
  readonly derivado = computed(() => {
    const guardado = this._guardado();
    if (guardado === null) return null;
    return {
      areaM2: guardado.area_m2,
      perimeterM: guardado.perimetro_m,
      lados: guardado.lados,
      caudalEfectivoM3h: guardado.caudal_efectivo_m3h,
      caudalOrigen: guardado.caudal_origen,
      caudalSugeridoM3h: guardado.caudal_sugerido_m3h,
      alertas: guardado.alertas,
    };
  });

  readonly alertas = computed<AdvertenciaApi[]>(() => this.derivado()?.alertas ?? []);

  readonly areaM2 = computed(() => this.derivado()?.areaM2 ?? this.metrics().areaM2);
  readonly areaHaLabel = computed(() => `${(this.areaM2() / 10000).toFixed(2)} ha`);
  readonly areaSqMLabel = computed(() => `(${formatThousands(this.areaM2())} m²)`);
  readonly perimeterLabel = computed(
    () => `${(this.derivado()?.perimeterM ?? this.metrics().perimeterM).toFixed(1)} m`,
  );
  readonly diagonalLabel = computed(() => `${this.metrics().diagonalM.toFixed(2)} m`);
  readonly verticesLabel = computed(() => {
    const lados = this.derivado()?.lados;
    return lados === undefined ? SHAPE_LABELS[this._state().shape] : `${lados} lados`;
  });
  readonly slopeLabel = computed(() => `${this._state().slopePct.toFixed(1)} %`);
  readonly desnivelLabel = computed(
    () => `${this.desnivelM().toFixed(2)} m (${this._state().slopePct}% pend.)`,
  );
  readonly caudalLabel = computed(() => {
    const caudal = this.derivado()?.caudalEfectivoM3h;
    if (caudal !== undefined) return `${caudal} m³/h`;
    const informado = this._state().flowM3h;
    return informado === null ? 'Lo asigna el sistema' : `${informado} m³/h`;
  });
  readonly caudalOrigenLabel = computed(() => {
    const derivado = this.derivado();
    if (derivado === null) return 'Todavía sin guardar';
    return derivado.caudalOrigen === 'cliente'
      ? 'Informado por vos'
      : `Asumido por el sistema (sugerido ${derivado.caudalSugeridoM3h ?? '—'} m³/h)`;
  });
  readonly infiltrationLabel = computed(() => {
    const suelo = this._suelos().find((option) => option.codigo === this._state().soil);
    if (suelo !== undefined) return `Infiltración: ${suelo.infiltracion_mm_h} mm/h`;
    const option = SOIL_OPTIONS.find((soil) => soil.value === this._state().soil);
    return option ? `Infiltración: ${option.infiltration}` : '';
  });

  /** Comprobaciones reales del paso 1, no texto decorativo. */
  readonly validaciones = computed<Validacion[]>(() => {
    const state = this._state();
    const vertices = this.vertices();
    const cotas = state.dimensions;
    const rectangulo = state.shape === 'rectangulo';
    const area = areaPoligono(vertices);
    const completa =
      cotas.topM > 0 && cotas.leftM > 0 && (rectangulo || cotas.bottomM > 0);

    return [
      {
        ok: completa,
        texto: completa
          ? `${vertices.length} vértices con cotas completas`
          : 'Faltan cotas: el área tiene que ser mayor que cero',
      },
      {
        ok: area >= AREA_MINIMA_M2,
        texto:
          area >= AREA_MINIMA_M2
            ? `Área admisible para cultivo (${Math.round(area)} m² ≥ ${AREA_MINIMA_M2} m²)`
            : `Superficie insuficiente para cultivo (${Math.round(area)} m²)`,
      },
      {
        ok: !seAutoIntersecta(vertices),
        texto: seAutoIntersecta(vertices)
          ? 'El polígono se cruza a sí mismo: revisá los vértices'
          : 'Sin autointersección de aristas',
      },
      {
        ok: state.slopePct <= PENDIENTE_MAXIMA_PCT,
        texto:
          state.slopePct <= PENDIENTE_MAXIMA_PCT
            ? `Pendiente dentro del rango de riego (≤ ${PENDIENTE_MAXIMA_PCT}%)`
            : `Pendiente alta para riego (${state.slopePct}%)`,
      },
    ];
  });

  readonly areaCalculadaM2 = computed(() => areaPoligono(this.vertices()));

  readonly guardando = computed(() => this._estado() === 'guardando');
  readonly guardadoLabel = computed(() => {
    switch (this._estado()) {
      case 'cargando':
        return 'Cargando proyecto…';
      case 'guardando':
        return 'Guardando…';
      case 'guardado':
        return 'Terreno guardado';
      case 'error':
        return 'No se pudo guardar';
      default:
        return 'Sin guardar';
    }
  });

  /** Loads the project name, the saved terrain (if any) and the soil catalogue. */
  cargar(proyectoId: string): void {
    this._proyectoId.set(proyectoId);
    this._estado.set('cargando');
    this._error.set(null);

    forkJoin({
      proyecto: this.projectsApi.obtener(proyectoId),
      terreno: this.api.obtener(proyectoId).pipe(
        catchError((error: HttpErrorResponse) => {
          // 404 is the normal first pass: the project has no terrain yet.
          if (error.status !== 404) this._error.set(mensajeDeError(error));
          return of(null);
        }),
      ),
      suelos: this.api.suelos().pipe(catchError(() => of([] as SueloApi[]))),
    }).subscribe({
      next: ({ proyecto, terreno, suelos }) => {
        this._nombreProyecto.set(proyecto.nombre);
        this._suelos.set(suelos);
        if (terreno === null && !this._nombreEditado()) {
          // El usuario ya nombró el proyecto: no le pedimos otro nombre igual.
          this._state.update((state) => ({ ...state, name: proyecto.nombre }));
        }
        if (terreno !== null) this.aplicarTerreno(terreno);
        this._estado.set(terreno === null ? 'inicial' : 'guardado');
      },
      error: (error: HttpErrorResponse) => {
        this._error.set(mensajeDeError(error));
        this._estado.set('error');
      },
    });
  }

  /** Saves the terrain: `PUT` the first time, `PATCH` afterwards. */
  guardar(): void {
    const proyectoId = this._proyectoId();
    if (proyectoId === null || this.guardando()) return;

    this._estado.set('guardando');
    this._error.set(null);
    this.api.guardar(proyectoId, this.aPayload(), this._guardado() !== null).subscribe({
      next: (terreno) => {
        this._guardado.set(terreno);
        this._estado.set('guardado');
      },
      error: (error: HttpErrorResponse) => {
        this._error.set(mensajeDeError(error));
        this._estado.set('error');
      },
    });
  }

  setName(name: string): void {
    this._nombreEditado.set(true);
    this._state.update((state) => ({ ...state, name }));
  }

  setShape(shape: TerrainState['shape']): void {
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

  setFlow(flowM3h: number | null): void {
    this._state.update((state) => ({ ...state, flowM3h }));
  }

  setStaticLevel(staticLevelM: number | null): void {
    this._state.update((state) => ({ ...state, staticLevelM }));
  }

  setNombreEditado(): void {
    this._nombreEditado.set(true);
  }

  shapeLabel(shape: TerrainState['shape']): string {
    return SHAPE_OPTIONS.find((option) => option.value === shape)?.label ?? '';
  }

  /** Payload for `PUT`/`PATCH`: the mockup's cotas become real vertices. */
  aPayload() {
    const state = this._state();
    return {
      nombre_parcela: state.name.trim() || 'Mi parcela',
      forma: FORMA_API[state.shape],
      vertices: toVertices(state.dimensions, state.shape),
      suelo_codigo: state.soil,
      pendiente_pct: state.slopePct,
      fuente_agua: state.waterSource,
      caudal_disponible_m3h: state.flowM3h,
      profundidad_nivel_dinamico_m: state.staticLevelM,
    };
  }

  private aplicarTerreno(terreno: TerrenoApi): void {
    const dimensions = fromVertices(terreno.geometria.vertices);
    this._state.set({
      name: terreno.nombre_parcela,
      shape: formaDeApi(terreno.forma),
      dimensions: dimensions ?? { ...INITIAL_TERRAIN.dimensions },
      soil: terreno.suelo_codigo as SoilType,
      slopePct: terreno.pendiente_pct,
      waterSource: terreno.fuente_agua as WaterSource,
      flowM3h: terreno.caudal_disponible_m3h,
      staticLevelM: terreno.profundidad_nivel_dinamico_m,
    });
    this._guardado.set(terreno);
  }
}

function formaDeApi(forma: TerrenoApi['forma']): TerrainState['shape'] {
  return forma === 'poligono' ? 'libre' : forma;
}

function formatThousands(value: number): string {
  return Math.round(value)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}
