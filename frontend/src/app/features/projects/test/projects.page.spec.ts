import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { ProjectsPage } from '../projects.page';

@Component({ template: '' })
class PantallaVacia {}

const PROYECTO_API = {
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
};

describe('ProjectsPage', () => {
  let http: HttpTestingController;
  let router: Router;
  let navegaciones: unknown[][];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProjectsPage],
      providers: [
        provideRouter([
          { path: 'projects', component: PantallaVacia },
          { path: 'proyectos/:proyectoId/terreno', component: PantallaVacia },
          { path: 'proyectos/:proyectoId/cultivos', component: PantallaVacia },
          { path: 'proyectos/:proyectoId/riego', component: PantallaVacia },
          { path: 'proyectos/:proyectoId/resultado', component: PantallaVacia },
        ]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    navegaciones = [];
    router.navigate = ((comandos: unknown[]) => {
      navegaciones.push(comandos);
      return Promise.resolve(true);
    }) as Router['navigate'];
  });

  afterEach(() => http.verify());

  async function render() {
    const fixture = TestBed.createComponent(ProjectsPage);
    await fixture.whenStable();
    http.expectOne('http://localhost:8000/proyectos').flush([]);
    await fixture.whenStable();
    return fixture;
  }

  type Fixture = Awaited<ReturnType<typeof render>>;

  function boton(fixture: Fixture, texto: string): HTMLButtonElement {
    return Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((candidate) => candidate.textContent?.includes(texto))!;
  }

  it('opens step 1 with the real id right after creating the project', async () => {
    const fixture = await render();

    boton(fixture, '+ Nuevo proyecto').click();
    await fixture.whenStable();

    const input = fixture.nativeElement.querySelector('#projectName') as HTMLInputElement;
    input.value = 'Los Olivos';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await fixture.whenStable();

    (fixture.nativeElement.querySelector('form') as HTMLFormElement).dispatchEvent(
      new Event('submit', { bubbles: true }),
    );
    await fixture.whenStable();
    http.expectOne('http://localhost:8000/proyectos').flush(PROYECTO_API);
    await fixture.whenStable();

    expect(navegaciones).toEqual([['/proyectos', 'p-4', 'terreno']]);
  });

  it('opens the step the card progress points at, not always step 1', async () => {
    const fixture = TestBed.createComponent(ProjectsPage);
    await fixture.whenStable();
    http.expectOne('http://localhost:8000/proyectos').flush([
      {
        id: 'p-1',
        nombre: 'Mi parcela',
        zona: 'Valle Central',
        unidad: 'metric',
        estado: 'en_progreso',
        area_m2: 2100,
        cultivos_count: 1,
        sistema_tipo: null,
        pendiente_pct: 2,
        num_sectores: null,
        geometria: null,
        ultimo_paso_completado: 2,
        actualizado_en: '2026-11-21T11:06:00',
        version: 1,
      },
    ]);
    await fixture.whenStable();

    boton(fixture, 'Continuar (Paso 3)').click();
    await fixture.whenStable();

    expect(navegaciones).toEqual([['/proyectos', 'p-1', 'riego']]);
  });

  it('opens the report from a finished project card', async () => {
    const fixture = TestBed.createComponent(ProjectsPage);
    await fixture.whenStable();
    http.expectOne('http://localhost:8000/proyectos').flush([
      {
        id: 'p-9',
        nombre: 'Los Olivos',
        zona: 'Valle Central',
        unidad: 'metric',
        estado: 'completado',
        area_m2: 2100,
        cultivos_count: 1,
        sistema_tipo: 'goteo',
        pendiente_pct: 2,
        num_sectores: 2,
        geometria: null,
        ultimo_paso_completado: 4,
        actualizado_en: '2026-11-21T11:06:00',
        version: 1,
      },
    ]);
    await fixture.whenStable();

    boton(fixture, 'Abrir proyecto').click();
    await fixture.whenStable();

    expect(navegaciones).toEqual([['/proyectos', 'p-9', 'resultado']]);
  });

  it('sends the toolbar and the header new-project buttons to the same modal', async () => {
    const fixture = await render();

    boton(fixture, '+ Nuevo proyecto').click();
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('#projectName')).not.toBeNull();
  });
});
