import { TestBed } from '@angular/core/testing';
import { ProjectCard } from '../components/project-card/project-card';
import { PROJECT_FIXTURES } from '../data/project.fixtures';
import { ProyectoListadoApi } from '../models/project.model';
import { toProject } from '../state/projects.store';

const RECTANGULO: ProyectoListadoApi['geometria'] = {
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

const CON_TERRENO: ProyectoListadoApi = {
  id: 'p-1',
  nombre: 'Los Olivos',
  zona: 'Valle Central',
  unidad: 'metric',
  estado: 'en_progreso',
  area_m2: 2400,
  cultivos_count: 0,
  sistema_tipo: null,
  pendiente_pct: 2,
  num_sectores: null,
  geometria: RECTANGULO,
  ultimo_paso_completado: 1,
  actualizado_en: '2026-11-21T11:06:00',
  version: 1,
};

const SIN_TERRENO: ProyectoListadoApi = {
  ...CON_TERRENO,
  id: 'p-2',
  nombre: 'Sin plano',
  area_m2: null,
  pendiente_pct: null,
  geometria: null,
  ultimo_paso_completado: 1,
};

describe('ProjectCard', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [ProjectCard] }).compileComponents();
  });

  async function render(index: number) {
    const fixture = TestBed.createComponent(ProjectCard);
    fixture.componentRef.setInput('project', PROJECT_FIXTURES[index]);
    await fixture.whenStable();
    return fixture;
  }

  it('renders the project identity and its area in the mockup format', async () => {
    const fixture = await render(0);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Mi parcela');
    expect(text).toContain('Valle Central');
    expect(text).toContain('21/11 11:06');
    expect(text).toContain('0.32 ha (3,200 m²)');
    expect(text).toContain('2 cultivos');
  });

  it('renders the irrigation summary and the hydraulic specs', async () => {
    const fixture = await render(0);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Riego por goteo');
    expect(text).toContain('2 sectores');
    expect(text).toContain('Pozo artesiano · Tanque 5.000 L · Bomba 1 HP');
  });

  it('overlays the wizard step and the dimensions on the schematic', async () => {
    const fixture = await render(0);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Paso 4: Resultado');
    expect(text).toContain('60.00 × 40.00 m');
  });

  it('draws the reference schematic for each fixture', async () => {
    const first = await render(0);
    expect(
      first.nativeElement.querySelectorAll('app-preview-mi-parcela polygon').length,
    ).toBeGreaterThan(1);

    const third = await render(2);
    const text = third.nativeElement.textContent as string;
    expect(text).toContain('Paso 3: Sistema');
    expect(text).toContain('0.75 ha (7,500 m²)');
    expect(third.nativeElement.querySelector('app-preview-finca-el-paraiso')).not.toBeNull();
  });

  it('labels a completed project with its status and next action', async () => {
    const fixture = await render(0);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Cómputo listo');
    expect(text).toContain('Abrir proyecto');
  });

  it('renders an inline SVG for every icon of the three fixtures', async () => {
    for (const index of [0, 1, 2]) {
      const fixture = await render(index);
      const icons = Array.from(
        fixture.nativeElement.querySelectorAll('ng-icon') as NodeListOf<HTMLElement>,
      );

      expect(icons.length).toBeGreaterThan(0);
      expect(icons.filter((icon) => icon.querySelector('svg') === null).length).toBe(0);
    }
  });

  it('labels an in-progress project with the step it resumes', async () => {
    const fixture = await render(1);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Falta cálculo hidráulico');
    expect(text).toContain('Continuar (Paso 2)');
    expect(text).toContain('1.10 ha (11,000 m²)');
  });

  it('emits the project when the primary action is used', async () => {
    const fixture = await render(0);
    let emitted: unknown;

    fixture.componentInstance.open.subscribe((project) => (emitted = project));
    const action = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.includes('Abrir proyecto'))!;

    action.click();

    expect(emitted).toBe(PROJECT_FIXTURES[0]);
  });

  async function renderApi(payload: ProyectoListadoApi) {
    const fixture = TestBed.createComponent(ProjectCard);
    fixture.componentRef.setInput('project', toProject(payload));
    await fixture.whenStable();
    return fixture;
  }

  it('draws the contour of the saved terrain with its real proportions', async () => {
    const fixture = await renderApi(CON_TERRENO);
    const poligono = fixture.nativeElement.querySelector('svg polygon') as SVGPolygonElement;

    expect(poligono).not.toBeNull();
    const puntos = (poligono.getAttribute('points') ?? '')
      .trim()
      .split(/\s+/)
      .map((par) => par.split(',').map(Number));
    expect(puntos.length).toBe(4);

    const xs = puntos.map(([x]) => x);
    const ys = puntos.map(([, y]) => y);
    const proporcion =
      (Math.max(...xs) - Math.min(...xs)) / (Math.max(...ys) - Math.min(...ys));
    // Un rectángulo de 60 × 40 m no se puede dibujar deformado.
    expect(proporcion).toBeCloseTo(1.5, 1);

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('0.24 ha (2,400 m²)');
    expect(texto).toContain('Pendiente 2 %');
    expect(texto).toContain('Sin definir');
    expect(texto).toContain('Paso 2: Cultivos');
    expect(texto).toContain('60 × 40 m');
  });

  it('keeps the empty placeholder and says "Sin definir" without terrain', async () => {
    const fixture = await renderApi(SIN_TERRENO);
    const texto = fixture.nativeElement.textContent as string;

    expect(texto).toContain('Sin terreno definido');
    expect(texto).toContain('Sin definir');
    expect(texto).not.toContain('0.00 ha');
    expect(texto).toContain('Paso 1: Terreno');
  });
});
