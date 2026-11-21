import { HttpErrorResponse } from '@angular/common/http';
import { Service, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { ProjectsApi } from '../projects.api';
import {
  CreateProjectInput,
  EstadoProyectoApi,
  Project,
  ProjectFilter,
  ProjectSort,
  ProyectoApi,
  ProyectoListadoApi,
} from '../models/project.model';
import { formatModifiedAt } from '../utils/project-format';

const COMPARATORS: Record<ProjectSort, (a: Project, b: Project) => number> = {
  recent: (a, b) => b.modifiedAt.localeCompare(a.modifiedAt),
  area_desc: (a, b) => b.areaM2 - a.areaM2,
  name: (a, b) => a.name.localeCompare(b.name, 'es'),
};

const ESTADO_LABEL: Record<EstadoProyectoApi, string> = {
  borrador: 'Borrador',
  en_progreso: 'En progreso',
  completado: 'Cómputo listo',
};

const PASO_LABEL: Record<number, string> = {
  0: 'Pendiente de terreno',
  1: 'Pendiente de cultivos',
  2: 'Pendiente de sistema',
  3: 'Pendiente de resultado',
};

/**
 * Projects list state, backed by the API.
 *
 * The collection, the search term, the filter and the sort order are signals; the
 * card view model is mapped from the backend payload so the grid never invents a
 * figure. Creating a project hits the API and returns the real project (with its
 * id) for the wizard hand-off.
 */
@Service()
export class ProjectsStore {
  private readonly api = inject(ProjectsApi);

  private readonly _projects = signal<Project[]>([]);
  private readonly _search = signal('');
  private readonly _filter = signal<ProjectFilter>('all');
  private readonly _sort = signal<ProjectSort>('recent');
  private readonly _loading = signal(false);
  private readonly _error = signal<string | null>(null);

  readonly projects = this._projects.asReadonly();
  readonly search = this._search.asReadonly();
  readonly filter = this._filter.asReadonly();
  readonly sort = this._sort.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly error = this._error.asReadonly();

  readonly counts = computed(() => {
    const projects = this._projects();
    return {
      all: projects.length,
      completed: projects.filter((project) => project.status === 'completed').length,
      in_progress: projects.filter((project) => project.status === 'in_progress').length,
    };
  });

  readonly visibleProjects = computed(() => {
    const term = this._search().trim().toLowerCase();
    const filter = this._filter();

    const filtered = this._projects()
      .filter((project) => filter === 'all' || project.status === filter)
      .filter((project) => (term ? matches(project, term) : true));

    return [...filtered].sort(COMPARATORS[this._sort()]);
  });

  /** Loads the grid. Called every time the dashboard is entered. */
  cargar(): void {
    this._loading.set(true);
    this._error.set(null);
    this.api.listar().subscribe({
      next: (proyectos) => {
        this._projects.set(proyectos.map(toProject));
        this._loading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this._error.set(mensajeDeError(error));
        this._loading.set(false);
      },
    });
  }

  /** Creates the project in the backend and returns it with its real id. */
  crear(input: CreateProjectInput): Observable<ProyectoApi> {
    this._error.set(null);
    return this.api
      .crear({
        nombre: input.name.trim(),
        zona: input.location.trim() || null,
        unidad: input.unitSystem,
      })
      .pipe(
        tap({
          next: (proyecto) => {
            this._projects.update((projects) => [toProject(proyecto), ...projects]);
          },
          error: (error: HttpErrorResponse) => this._error.set(mensajeDeError(error)),
        }),
      );
  }

  setSearch(term: string): void {
    this._search.set(term);
  }

  setFilter(filter: ProjectFilter): void {
    this._filter.set(filter);
  }

  setSort(sort: ProjectSort): void {
    this._sort.set(sort);
  }
}

/** Maps the backend payload to the card view model. */
export function toProject(payload: ProyectoListadoApi | ProyectoApi): Project {
  const completado = payload.estado === 'completado';
  const paso = 'ultimo_paso_completado' in payload ? payload.ultimo_paso_completado : 0;
  const siguiente = Math.min(Math.max(paso + 1, 1), 4);
  const cultivos = 'cultivos_count' in payload ? payload.cultivos_count : 0;
  const area = 'area_m2' in payload ? (payload.area_m2 ?? 0) : 0;
  const sistema = 'sistema_tipo' in payload ? payload.sistema_tipo : null;

  return {
    id: payload.id,
    name: payload.nombre,
    location: payload.zona ?? 'Sin ubicación',
    modifiedAt: formatModifiedAt(payload.actualizado_en.slice(0, 16)),
    status: completado ? 'completed' : 'in_progress',
    statusLabel: completado ? ESTADO_LABEL.completado : PASO_LABEL[paso] ?? 'En progreso',
    statusIcon: completado ? 'check_circle' : 'pending',
    statusTone: completado ? 'text-secondary' : 'text-tertiary-container',
    headerIcon: completado ? 'verified' : 'pending',
    headerTone: completado ? 'text-secondary' : 'text-tertiary-container',
    headerTitle: completado ? 'Proyecto verificado' : 'Proyecto en progreso',
    unitSystem: payload.unidad,
    areaM2: area,
    sectorsLabel: area > 0 ? `${Math.round(area)} m²` : 'Pendiente diseño',
    speciesLabel: cultivos === 1 ? '1 cultivo' : `${cultivos} cultivos`,
    irrigationType: sistema ? capitalizar(sistema) : 'Sin sistema',
    hydraulicSpecs: 'Sin definir',
    crops: [],
    preview: 'empty',
    stepLabel: completado ? 'Paso 4: Resultado' : `Paso ${siguiente}`,
    nextStep: completado
      ? { label: 'Abrir proyecto', icon: 'visibility' }
      : { label: `Continuar (Paso ${siguiente})`, icon: 'edit', step: siguiente },
  };
}

function capitalizar(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** One readable sentence for the most common backend failures. */
export function mensajeDeError(error: HttpErrorResponse): string {
  if (error.status === 0) {
    return 'No pudimos conectar con el servidor. Revisá que el backend esté corriendo.';
  }
  if (error.status === 401) {
    return 'Tu sesión venció. Volvé a ingresar.';
  }
  if (error.status === 403) {
    return 'No tenés permiso para esa acción.';
  }
  const detalle = typeof error.error?.detail === 'string' ? error.error.detail : '';
  return detalle || 'Algo salió mal. Probá de nuevo.';
}

function matches(project: Project, term: string): boolean {
  const haystack = [
    project.name,
    project.location,
    project.hydraulicSpecs,
    ...project.crops.map((crop) => crop.name),
  ]
    .join(' ')
    .toLowerCase();

  return haystack.includes(term);
}
