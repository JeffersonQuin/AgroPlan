import { Service, computed, signal } from '@angular/core';
import { PROJECT_FIXTURES } from '../data/project.fixtures';
import {
  CreateProjectInput,
  Project,
  ProjectFilter,
  ProjectSort,
} from '../models/project.model';
import { toLocalIso } from '../utils/project-format';

const COMPARATORS: Record<ProjectSort, (a: Project, b: Project) => number> = {
  recent: (a, b) => b.modifiedAt.localeCompare(a.modifiedAt),
  area_desc: (a, b) => b.areaM2 - a.areaM2,
  name: (a, b) => a.name.localeCompare(b.name, 'es'),
};

/**
 * Projects list state: the collection, the search term, the status filter and
 * the sort order, all derived into `visibleProjects`.
 *
 * Scope: presentation only. It seeds from local fixtures and creates projects
 * in memory; wire it to the backend when the projects endpoints exist.
 */
@Service()
export class ProjectsStore {
  private readonly _projects = signal<Project[]>([...PROJECT_FIXTURES]);
  private readonly _search = signal('');
  private readonly _filter = signal<ProjectFilter>('all');
  private readonly _sort = signal<ProjectSort>('recent');

  readonly projects = this._projects.asReadonly();
  readonly search = this._search.asReadonly();
  readonly filter = this._filter.asReadonly();
  readonly sort = this._sort.asReadonly();

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

  setSearch(term: string): void {
    this._search.set(term);
  }

  setFilter(filter: ProjectFilter): void {
    this._filter.set(filter);
  }

  setSort(sort: ProjectSort): void {
    this._sort.set(sort);
  }

  create(input: CreateProjectInput): Project {
    const project: Project = {
      id: `project-${Date.now()}`,
      name: input.name.trim(),
      location: input.location.trim() || 'Sin ubicación',
      modifiedAt: toLocalIso(new Date()),
      status: 'in_progress',
      statusLabel: 'Pendiente de terreno',
      statusIcon: 'pending',
      statusTone: 'text-tertiary-container',
      headerIcon: 'pending',
      headerTone: 'text-tertiary-container',
      headerTitle: 'Pendiente de terreno',
      unitSystem: input.unitSystem,
      areaM2: 0,
      sectorsLabel: 'Pendiente diseño',
      speciesLabel: '0 cultivos',
      irrigationType: 'Sin sistema',
      hydraulicSpecs: 'Sin definir',
      crops: [],
      preview: 'empty',
      stepLabel: 'Paso 1: Configuración',
      nextStep: { label: 'Continuar (Paso 1)', icon: 'edit', step: 1 },
    };

    this._projects.update((projects) => [project, ...projects]);
    return project;
  }
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
