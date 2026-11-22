import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ProyectoListadoApi } from '../models/project.model';
import { ProjectsStore } from '../state/projects.store';

/** Rectángulo de 60 × 40 m: el mismo contorno que dibuja la tarjeta. */
const RECTANGULO = {
  vertices: [
    { x: 0, y: 0 },
    { x: 60, y: 0 },
    { x: 60, y: 40 },
    { x: 0, y: 40 },
  ],
  cerrado: true,
  unidad: 'm',
  eje_y: 'norte',
};

const PROYECTOS: ProyectoListadoApi[] = [
  {
    id: 'p-1',
    nombre: 'Mi parcela',
    zona: 'Valle Central',
    unidad: 'metric',
    estado: 'completado',
    area_m2: 3200,
    cultivos_count: 2,
    sistema_tipo: 'goteo',
    pendiente_pct: 2,
    num_sectores: 2,
    geometria: RECTANGULO,
    ultimo_paso_completado: 4,
    actualizado_en: '2026-11-21T11:06:00.123456',
    version: 3,
  },
  {
    id: 'p-2',
    nombre: 'Parcela Norte',
    zona: 'Alto Valle',
    unidad: 'metric',
    estado: 'en_progreso',
    area_m2: 6400,
    cultivos_count: 1,
    sistema_tipo: null,
    pendiente_pct: 3.5,
    num_sectores: null,
    geometria: RECTANGULO,
    ultimo_paso_completado: 2,
    actualizado_en: '2026-11-20T09:30:00',
    version: 1,
  },
  {
    id: 'p-3',
    nombre: 'Finca El Paraíso - B',
    zona: 'Quebrada',
    unidad: 'metric',
    estado: 'en_progreso',
    area_m2: null,
    cultivos_count: 0,
    sistema_tipo: null,
    pendiente_pct: null,
    num_sectores: null,
    geometria: null,
    ultimo_paso_completado: 1,
    actualizado_en: '2026-11-19T18:00:00',
    version: 1,
  },
];

describe('ProjectsStore', () => {
  let store: ProjectsStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(ProjectsStore);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function cargar(): void {
    store.cargar();
    http.expectOne('http://localhost:8000/proyectos').flush(PROYECTOS);
  }

  it('loads the projects from the backend', () => {
    expect(store.projects()).toEqual([]);

    cargar();

    expect(store.projects().length).toBe(3);
    expect(store.counts()).toEqual({ all: 3, completed: 1, in_progress: 2 });
    expect(store.loading()).toBe(false);
    expect(store.error()).toBeNull();
  });

  it('maps the backend payload to the card', () => {
    cargar();
    const completado = store.projects().find((project) => project.id === 'p-1')!;

    expect(completado.name).toBe('Mi parcela');
    expect(completado.location).toBe('Valle Central');
    expect(completado.status).toBe('completed');
    expect(completado.areaM2).toBe(3200);
    expect(completado.speciesLabel).toBe('2 cultivos');
    expect(completado.irrigationType).toBe('Goteo');
    expect(completado.modifiedAt).toBe('21/11 11:06');
  });

  it('draws the terrain, the species, the irrigation and the slope the project saves', () => {
    cargar();
    const terreno = store.projects().find((project) => project.id === 'p-1')!;

    expect(terreno.preview).toBe('terreno');
    expect(terreno.geometria?.vertices.length).toBe(4);
    expect(terreno.sectorsLabel).toBe('2 sectores');
    expect(terreno.hydraulicSpecs).toBe('Pendiente 2 %');
    expect(terreno.stepLabel).toBe('Paso 4: Resultado');
    expect(terreno.dimensionsLabel).toBe('60 × 40 m');

    // Terreno y cultivos, sin sistema de riego: la fila de riego no inventa valores.
    const sinSistema = store.projects().find((project) => project.id === 'p-2')!;
    expect(sinSistema.preview).toBe('terreno');
    expect(sinSistema.sectorsLabel).toBe('Sin definir');
    expect(sinSistema.irrigationType).toBe('Sin definir');
    expect(sinSistema.hydraulicSpecs).toBe('Pendiente 3.5 %');
    expect(sinSistema.statusLabel).toBe('Pendiente de sistema');
    expect(sinSistema.nextStep.step).toBe(3);
  });

  it('leaves a project without terrain on step 1 with no invented figures', () => {
    cargar();
    const sinTerreno = store.projects().find((project) => project.id === 'p-3')!;

    expect(sinTerreno.areaM2).toBeNull();
    expect(sinTerreno.preview).toBe('empty');
    expect(sinTerreno.geometria).toBeNull();
    expect(sinTerreno.dimensionsLabel).toBeUndefined();
    expect(sinTerreno.hydraulicSpecs).toBe('Sin definir');
    expect(sinTerreno.statusLabel).toBe('Pendiente de terreno');
    expect(sinTerreno.nextStep.step).toBe(1);
    expect(sinTerreno.stepLabel).toBe('Paso 1: Terreno');
  });

  it('keeps the search, the filter and the sort over the loaded projects', () => {
    cargar();

    expect(store.visibleProjects().map((project) => project.name)).toEqual([
      'Mi parcela',
      'Parcela Norte',
      'Finca El Paraíso - B',
    ]);

    store.setFilter('completed');
    expect(store.visibleProjects().map((project) => project.name)).toEqual(['Mi parcela']);

    store.setFilter('all');
    store.setSort('area_desc');
    expect(store.visibleProjects()[0].name).toBe('Parcela Norte');
    expect(store.visibleProjects()[2].name).toBe('Finca El Paraíso - B');

    store.setSort('name');
    expect(store.visibleProjects()[0].name).toBe('Finca El Paraíso - B');

    store.setSearch('norte');
    expect(store.visibleProjects().map((project) => project.name)).toEqual(['Parcela Norte']);
  });

  it('creates the project in the backend and puts it first', () => {
    cargar();
    let creado = '';
    store
      .crear({ name: '  Los Olivos ', location: 'Valle Central', unitSystem: 'metric' })
      .subscribe((proyecto) => (creado = proyecto.id));

    const peticion = http.expectOne('http://localhost:8000/proyectos');
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body).toEqual({
      nombre: 'Los Olivos',
      zona: 'Valle Central',
      unidad: 'metric',
    });
    peticion.flush({
      id: 'p-4',
      nombre: 'Los Olivos',
      zona: 'Valle Central',
      unidad: 'metric',
      estado: 'borrador',
      paso_actual: 1,
      ultimo_paso_completado: 0,
      version: 1,
      corrida_actual_id: null,
      creado_en: '2026-11-21T12:00:00',
      actualizado_en: '2026-11-21T12:00:00',
    });

    expect(creado).toBe('p-4');
    expect(store.projects().length).toBe(4);
    expect(store.projects()[0].name).toBe('Los Olivos');
    expect(store.visibleProjects()[0].name).toBe('Los Olivos');
  });

  it('explains a FastAPI validation error field by field', () => {
    store.cargar();
    http.expectOne('http://localhost:8000/proyectos').flush(
      {
        detail: [
          { loc: ['body', 'caudal_disponible_m3h'], msg: 'Input should be greater than 0' },
          { loc: ['body', 'vertices'], msg: 'List should have at least 3 items' },
        ],
      },
      { status: 422, statusText: 'Unprocessable Content' },
    );

    expect(store.error()).toBe(
      'Revisá estos datos → caudal_disponible_m3h: tiene que ser mayor que 0 · vertices: List should have at least 3 items',
    );
  });

  it('reports a readable error when the backend is down', () => {
    store.cargar();
    http
      .expectOne('http://localhost:8000/proyectos')
      .error(new ProgressEvent('error'), { status: 0 });

    expect(store.loading()).toBe(false);
    expect(store.error()).toContain('No pudimos conectar con el servidor');
  });

  it('surfaces the backend detail when creating fails', () => {
    cargar();
    let mensaje = '';
    store
      .crear({ name: 'Los Olivos', location: '', unitSystem: 'metric' })
      .subscribe({ error: (error) => (mensaje = error.status.toString()) });

    http
      .expectOne('http://localhost:8000/proyectos')
      .flush({ detail: 'El proyecto ya existe' }, { status: 409, statusText: 'Conflict' });

    expect(mensaje).toBe('409');
    expect(store.error()).toBe('El proyecto ya existe');
    expect(store.projects().length).toBe(3);
  });
});
