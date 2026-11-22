import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ProjectCreateModal } from '../components/project-create-modal/project-create-modal';
import { ProjectsStore } from '../state/projects.store';

describe('ProjectCreateModal', () => {
  let store: ProjectsStore;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProjectCreateModal],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    store = TestBed.inject(ProjectsStore);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function render() {
    const fixture = TestBed.createComponent(ProjectCreateModal);
    await fixture.whenStable();
    return fixture;
  }

  type Fixture = Awaited<ReturnType<typeof render>>;

  function query<T extends Element>(fixture: Fixture, selector: string): T {
    return fixture.nativeElement.querySelector(selector) as T;
  }

  async function type(fixture: Fixture, selector: string, value: string) {
    const input = query<HTMLInputElement>(fixture, selector);
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await fixture.whenStable();
  }

  it('starts on the metric system with an empty counter', async () => {
    const fixture = await render();

    expect(fixture.nativeElement.textContent).toContain('0 / 60');
    expect(
      Array.from(
        fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
      ).find((button) => button.textContent?.includes('Metros'))!.getAttribute('aria-pressed'),
    ).toBe('true');
  });

  it('updates the character counter as the name is typed', async () => {
    const fixture = await render();

    await type(fixture, '#projectName', 'Los Olivos');

    expect(fixture.nativeElement.textContent).toContain('10 / 60');
  });

  it('refuses to create a project without a name', async () => {
    const fixture = await render();

    query<HTMLFormElement>(fixture, 'form').dispatchEvent(new Event('submit'));
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('Poné un nombre para el proyecto.');
    http.expectNone('http://localhost:8000/proyectos');
  });

  it('creates the project in the backend and hands the id to the page', async () => {
    const fixture = await render();
    let creado = '';
    fixture.componentInstance.created.subscribe((id) => (creado = id));

    await type(fixture, '#projectName', 'Los Olivos');
    await type(fixture, '#projectLocation', 'Valle Central');
    query<HTMLFormElement>(fixture, 'form').dispatchEvent(new Event('submit', { bubbles: true }));
    await fixture.whenStable();

    const peticion = http.expectOne('http://localhost:8000/proyectos');
    expect(peticion.request.method).toBe('POST');
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
    await fixture.whenStable();

    expect(creado).toBe('p-4');
    expect(store.projects().length).toBe(1);
    expect(store.projects()[0].name).toBe('Los Olivos');
  });

  it('shows the backend error and keeps the dialog open', async () => {
    const fixture = await render();
    let creado = '';
    fixture.componentInstance.created.subscribe((id) => (creado = id));

    await type(fixture, '#projectName', 'Los Olivos');
    query<HTMLFormElement>(fixture, 'form').dispatchEvent(new Event('submit', { bubbles: true }));
    await fixture.whenStable();

    http
      .expectOne('http://localhost:8000/proyectos')
      .flush({ detail: 'El proyecto ya existe' }, { status: 409, statusText: 'Conflict' });
    await fixture.whenStable();

    expect(creado).toBe('');
    expect(fixture.nativeElement.textContent).toContain('El proyecto ya existe');
  });

  it('emits close when the dialog is dismissed', async () => {
    const fixture = await render();
    let closed = false;
    fixture.componentInstance.close.subscribe(() => (closed = true));

    const cancel = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.trim() === 'Cancelar')!;
    cancel.click();

    expect(closed).toBe(true);
  });
});
