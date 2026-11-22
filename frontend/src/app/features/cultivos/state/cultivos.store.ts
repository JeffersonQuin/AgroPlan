import { HttpErrorResponse } from '@angular/common/http';
import { Service, computed, inject, signal } from '@angular/core';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ProjectsApi } from '../../projects/projects.api';
import { mensajeDeError } from '../../projects/state/projects.store';
import { CultivosApi } from '../cultivos.api';
import { CultivoCatalogoApi } from '../models/cultivos.model';

export type EstadoPaso2 = 'inicial' | 'cargando' | 'listo' | 'error';

/**
 * Step 2 reads only: the project, its terrain and the crop catalogue.
 *
 * Nothing is written and the agent is not called here — that happens once, in the
 * final summary. The products the user picks live in `WizardDraftStore`.
 */
@Service()
export class CultivosStore {
  private readonly api = inject(CultivosApi);
  private readonly projectsApi = inject(ProjectsApi);

  private readonly _nombreProyecto = signal('');
  private readonly _areaM2 = signal(0);
  private readonly _caudalM3h = signal(0);
  private readonly _sueloCodigo = signal('');
  private readonly _verticesTerreno = signal<{ x: number; y: number }[]>([]);
  private readonly _catalogo = signal<CultivoCatalogoApi[]>([]);
  private readonly _estado = signal<EstadoPaso2>('inicial');
  private readonly _error = signal<string | null>(null);

  readonly nombreProyecto = this._nombreProyecto.asReadonly();
  readonly areaM2 = this._areaM2.asReadonly();
  readonly caudalM3h = this._caudalM3h.asReadonly();
  readonly sueloCodigo = this._sueloCodigo.asReadonly();
  readonly verticesTerreno = this._verticesTerreno.asReadonly();
  readonly catalogo = this._catalogo.asReadonly();
  readonly estado = this._estado.asReadonly();
  readonly error = this._error.asReadonly();

  readonly cargando = computed(() => this._estado() === 'cargando');

  /** Opciones del selector de especie: el catálogo activo del backend. */
  readonly opcionesCultivo = computed(() =>
    this._catalogo().map((cultivo) => ({
      value: cultivo.codigo,
      label: cultivo.nombre,
      demanda: cultivo.demanda_agua_l_m2_dia,
      ciclo: cultivo.ciclo_dias,
      kc: cultivo.kc,
      color: cultivo.color,
    })),
  );

  cargar(proyectoId: string): void {
    this._estado.set('cargando');
    this._error.set(null);

    forkJoin({
      proyecto: this.projectsApi.obtener(proyectoId),
      terreno: this.api.terreno(proyectoId).pipe(catchError(() => of(null))),
      catalogo: this.api.catalogo().pipe(catchError(() => of([] as CultivoCatalogoApi[]))),
    }).subscribe({
      next: ({ proyecto, terreno, catalogo }) => {
        this._nombreProyecto.set(proyecto.nombre);
        this._areaM2.set(terreno?.area_m2 ?? 0);
        this._caudalM3h.set(terreno?.caudal_efectivo_m3h ?? 0);
        this._sueloCodigo.set(terreno?.suelo_codigo ?? '');
        this._verticesTerreno.set(terreno?.geometria?.vertices ?? []);
        this._catalogo.set(catalogo.filter((cultivo) => cultivo.activo));
        this._estado.set('listo');
      },
      error: (error: HttpErrorResponse) => {
        this._error.set(mensajeDeError(error));
        this._estado.set('error');
      },
    });
  }
}
