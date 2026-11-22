import { HttpErrorResponse } from '@angular/common/http';
import { Service, computed, inject, signal } from '@angular/core';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ProjectsApi } from '../../projects/projects.api';
import { mensajeDeError } from '../../projects/state/projects.store';
import { FuenteAguaApi, WATER_SOURCE_OPTIONS } from '../../terrain/models/terrain.model';
import { RiegoApi } from '../riego.api';

export type EstadoPaso3 = 'inicial' | 'cargando' | 'listo' | 'error';

/**
 * Step 3 reads only: the project and the water source its terrain already declared.
 *
 * The irrigation system, the network trace, the sectors and every figure are decided by
 * the agent in step 4. Here nothing is written, nothing is computed and the agent is not
 * called — the restrictions the user picks live in `WizardDraftStore`.
 */
@Service()
export class RiegoStore {
  private readonly api = inject(RiegoApi);
  private readonly projectsApi = inject(ProjectsApi);

  private readonly _nombreProyecto = signal('');
  private readonly _areaM2 = signal(0);
  private readonly _fuenteAgua = signal<FuenteAguaApi>('pozo');
  private readonly _caudalM3h = signal(0);
  private readonly _estado = signal<EstadoPaso3>('inicial');
  private readonly _error = signal<string | null>(null);

  readonly nombreProyecto = this._nombreProyecto.asReadonly();
  readonly areaM2 = this._areaM2.asReadonly();
  readonly fuenteAgua = this._fuenteAgua.asReadonly();
  readonly caudalM3h = this._caudalM3h.asReadonly();
  readonly estado = this._estado.asReadonly();
  readonly error = this._error.asReadonly();

  readonly cargando = computed(() => this._estado() === 'cargando');

  /** Etiqueta de la fuente, con el mismo vocabulario del paso 1. */
  readonly fuenteLabel = computed(
    () =>
      WATER_SOURCE_OPTIONS.find((opcion) => opcion.value === this._fuenteAgua())?.label ?? '',
  );

  /** Sin caudal el diseño queda condicionado: el paso avisa, no bloquea. */
  readonly sinCaudal = computed(() => this._caudalM3h() <= 0);

  /**
   * El paso 1 ya declara un depósito como fuente (tanque o cisterna): preguntar
   * "¿ya tenés tanque?" sería preguntar dos veces lo mismo.
   */
  readonly fuenteEsDeposito = computed(
    () => this._fuenteAgua() === 'tanque' || this._fuenteAgua() === 'cisterna',
  );

  readonly fuenteDepositoLabel = computed(() =>
    this._fuenteAgua() === 'cisterna' ? 'cisterna' : 'tanque',
  );

  cargar(proyectoId: string): void {
    this._estado.set('cargando');
    this._error.set(null);

    forkJoin({
      proyecto: this.projectsApi.obtener(proyectoId),
      terreno: this.api.terreno(proyectoId).pipe(catchError(() => of(null))),
    }).subscribe({
      next: ({ proyecto, terreno }) => {
        this._nombreProyecto.set(proyecto.nombre);
        this._areaM2.set(terreno?.area_m2 ?? 0);
        this._fuenteAgua.set(terreno?.fuente_agua ?? 'pozo');
        this._caudalM3h.set(terreno?.caudal_efectivo_m3h ?? 0);
        this._estado.set('listo');
      },
      error: (error: HttpErrorResponse) => {
        this._error.set(mensajeDeError(error));
        this._estado.set('error');
      },
    });
  }
}
