import { HttpErrorResponse } from '@angular/common/http';
import { Service, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { ProjectsApi } from '../projects.api';
import {
  CreateProjectInput,
  EstadoProyectoApi,
  GeometriaTerrenoApi,
  Project,
  ProjectFilter,
  ProjectSort,
  ProyectoApi,
  ProyectoListadoApi,
} from '../models/project.model';
import { formatModifiedAt } from '../utils/project-format';

const COMPARATORS: Record<ProjectSort, (a: Project, b: Project) => number> = {
  recent: (a, b) => b.modifiedAt.localeCompare(a.modifiedAt),
  area_desc: (a, b) => (b.areaM2 ?? 0) - (a.areaM2 ?? 0),
  name: (a, b) => a.name.localeCompare(b.name, 'es'),
};

const ESTADO_LABEL: Record<EstadoProyectoApi, string> = {
  borrador: 'Borrador',
  en_progreso: 'En progreso',
  completado: 'Cómputo listo',
};

/** What is still missing before the given wizard step, in card words. */
const PASO_LABEL: Record<number, string> = {
  0: 'Pendiente de terreno',
  1: 'Pendiente de cultivos',
  2: 'Pendiente de sistema',
  3: 'Pendiente de resultado',
};

/** Wizard step name for the chip over the schematic. */
const PASO_NOMBRE: Record<number, string> = {
  1: 'Terreno',
  2: 'Cultivos',
  3: 'Riego',
  4: 'Resultado',
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
  const cultivos = 'cultivos_count' in payload ? payload.cultivos_count : 0;
  const area = 'area_m2' in payload ? payload.area_m2 : null;
  const sistema = 'sistema_tipo' in payload ? payload.sistema_tipo : null;
  const pendiente = 'pendiente_pct' in payload ? (payload.pendiente_pct ?? null) : null;
  const sectores = 'num_sectores' in payload ? (payload.num_sectores ?? null) : null;
  const geometria = 'geometria' in payload ? (payload.geometria ?? null) : null;

  // Sin terreno guardado no hay avance posible: la tarjeta vuelve al paso 1 aunque
  // el backend ya hubiera contado un paso (el listado nunca lo hace, pero el
  // proyecto recién creado sí llega con la columna en cero).
  const siguiente = area === null ? 1 : Math.min(Math.max(paso + 1, 1), 4);

  return {
    id: payload.id,
    name: payload.nombre,
    location: payload.zona ?? 'Sin ubicación',
    modifiedAt: formatModifiedAt(payload.actualizado_en.slice(0, 16)),
    status: completado ? 'completed' : 'in_progress',
    statusLabel: completado
      ? ESTADO_LABEL.completado
      : (PASO_LABEL[siguiente - 1] ?? 'En progreso'),
    statusIcon: completado ? 'check_circle' : 'pending',
    statusTone: completado ? 'text-secondary' : 'text-tertiary-container',
    headerIcon: completado ? 'verified' : 'pending',
    headerTone: completado ? 'text-secondary' : 'text-tertiary-container',
    headerTitle: completado ? 'Proyecto verificado' : 'Proyecto en progreso',
    unitSystem: payload.unidad,
    areaM2: area,
    sectorsLabel: etiquetaDeSectores(sectores),
    speciesLabel: cultivos === 1 ? '1 cultivo' : `${cultivos} cultivos`,
    irrigationType: sistema ? capitalizar(sistema) : 'Sin definir',
    hydraulicSpecs:
      pendiente === null ? 'Sin definir' : `Pendiente ${formatearPendiente(pendiente)} %`,
    crops: [],
    preview: geometria ? 'terreno' : 'empty',
    geometria,
    stepLabel: `Paso ${siguiente}: ${PASO_NOMBRE[siguiente]}`,
    dimensionsLabel: geometria ? cotasDe(geometria) : undefined,
    nextStep: completado
      ? { label: 'Abrir proyecto', icon: 'visibility', step: siguiente }
      : { label: `Continuar (Paso ${siguiente})`, icon: 'edit', step: siguiente },
  };
}

function etiquetaDeSectores(sectores: number | null): string {
  if (sectores === null) return 'Sin definir';
  return sectores === 1 ? '1 sector' : `${sectores} sectores`;
}

/** 2 -> '2', 3.5 -> '3.5': the slope as saved, never padded with fake decimals. */
function formatearPendiente(pendiente: number): string {
  return Number.isInteger(pendiente) ? pendiente.toFixed(0) : pendiente.toFixed(1);
}

/** `60 × 40 m` from the bounding box of the saved contour. */
function cotasDe(geometria: GeometriaTerrenoApi): string {
  const xs = geometria.vertices.map((vertice) => vertice.x);
  const ys = geometria.vertices.map((vertice) => vertice.y);
  const ancho = Math.max(...xs) - Math.min(...xs);
  const alto = Math.max(...ys) - Math.min(...ys);
  return `${Math.round(ancho)} × ${Math.round(alto)} ${geometria.unidad}`;
}

function capitalizar(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** FastAPI devuelve `detail` como texto en los 4xx propios y como lista en los 422. */
interface ErrorValidacionApi {
  loc?: (string | number)[];
  msg?: string;
}

function detalleDeValidacion(detalle: unknown): string {
  if (!Array.isArray(detalle)) return '';
  const campos = (detalle as ErrorValidacionApi[])
    .map((item) => {
      const campo = (item.loc ?? []).filter((parte) => parte !== 'body').join('.');
      return campo && item.msg ? `${campo}: ${traducirValidacion(item.msg)}` : item.msg;
    })
    .filter(Boolean);
  return campos.join(' · ');
}

/** Los mensajes de pydantic vienen en inglés: los que usamos se traducen. */
function traducirValidacion(mensaje: string): string {
  if (mensaje.includes('greater than 0')) return 'tiene que ser mayor que 0';
  if (mensaje.includes('less than or equal')) return 'está por encima del máximo permitido';
  if (mensaje.includes('greater than or equal')) return 'está por debajo del mínimo permitido';
  if (mensaje.includes('String should have at least')) return 'está vacío o es demasiado corto';
  if (mensaje.includes('Extra inputs are not permitted')) {
    return 'el servidor no reconoce este campo: reiniciá el backend';
  }
  return mensaje;
}

/**
 * Errores de validación indexados por campo, para marcarlos en el formulario en vez
 * de mostrar un cartel genérico. La clave es el último tramo de `loc`.
 */
export function erroresDeCampo(error: HttpErrorResponse): Record<string, string> {
  const detalle = error.error?.detail;
  if (!Array.isArray(detalle)) return {};

  const errores: Record<string, string> = {};
  for (const item of detalle as ErrorValidacionApi[]) {
    const partes = item.loc ?? [];
    const campo = partes.filter((parte) => parte !== 'body').pop();
    if (typeof campo === 'string' && item.msg) {
      errores[campo] = traducirValidacion(item.msg);
    }
  }
  return errores;
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

  const detalle = error.error?.detail;
  if (typeof detalle === 'string' && detalle) return detalle;

  const validacion = detalleDeValidacion(detalle);
  if (validacion) return `Revisá estos datos → ${validacion}`;

  return 'Algo salió mal. Probá de nuevo.';
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
