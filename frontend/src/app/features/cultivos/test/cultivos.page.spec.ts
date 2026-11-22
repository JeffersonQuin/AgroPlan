import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { CultivosPage } from '../cultivos.page';

const PROYECTO = {
  id: 'p-1',
  nombre: 'Los Olivos',
  zona: 'Oruro',
  unidad: 'metric',
  estado: 'en_progreso',
  paso_actual: 2,
  ultimo_paso_completado: 1,
  version: 2,
  corrida_actual_id: null,
  creado_en: '2026-11-21T12:00:00',
  actualizado_en: '2026-11-21T12:30:00',
};

const CATALOGO = [
  {
    codigo: 'papa',
    nombre: 'Papa',
    icono: 'P',
    color: '#8D6E63',
    demanda_agua_l_m2_dia: 2,
    ciclo_dias: 120,
    kc: 1.15,
    densidad_plantas_m2: 4,
    profundidad_raiz_cm: 40,
    meses_siembra: [3],
    activo: true,
  },
  {
    codigo: 'lechuga',
    nombre: 'Lechuga',
    icono: 'L',
    color: '#7CB342',
    demanda_agua_l_m2_dia: 1.5,
    ciclo_dias: 65,
    kc: 1,
    densidad_plantas_m2: 9,
    profundidad_raiz_cm: 20,
    meses_siembra: null,
    activo: true,
  },
];

describe('CultivosPage (paso 2: sólo recoge datos)', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'proyectos/:proyectoId/cultivos', component: CultivosPage },
          { path: 'proyectos/:proyectoId/terreno', component: CultivosPage },
        ]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function montar() {
    const harness = await RouterTestingHarness.create('/proyectos/p-1/cultivos');
    http.expectOne('http://localhost:8000/proyectos/p-1').flush(PROYECTO);
    http.expectOne('http://localhost:8000/proyectos/p-1/terreno').flush({
      area_m2: 2100,
      caudal_efectivo_m3h: 3,
      suelo_codigo: 'franco_arenado',
      geometria: {
        vertices: [
          { x: 0, y: 0 },
          { x: 30, y: 0 },
          { x: 30, y: 70 },
          { x: 0, y: 70 },
        ],
      },
    });
    http.expectOne('http://localhost:8000/catalogos/cultivos').flush(CATALOGO);
    await harness.fixture.whenStable();
    return harness;
  }

  it('shows the project and an empty state that explains what to do', async () => {
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    expect(html.textContent).toContain('Los Olivos');
    expect(html.textContent).toContain('Todavía no elegiste productos');
    expect(html.textContent).toContain('Resumen del paso 2');
    expect(html.textContent).toContain('Este paso no consulta al agente');
    expect(html.textContent).toContain('Lo que vas a ver en el resumen');
    // El paso 2 no escribe nada: no hay llamadas de escritura pendientes.
    http.expectNone('http://localhost:8000/proyectos/p-1/agente');
  });

  it('collects a product from the catalogue without calling the API', async () => {
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    const agregar = html.querySelector(
      'button[aria-label="Agregar producto del catálogo"]',
    ) as HTMLButtonElement;
    agregar.click();
    await harness.fixture.whenStable();

    const tarjetas = html.querySelectorAll('article');
    expect(tarjetas.length).toBe(1);
    expect(html.textContent).toContain('Papa');
    expect(html.textContent).toContain('Del catálogo');
    expect(html.textContent).toContain('resumen');
    expect(html.textContent).toContain('Con 1 producto(s) el agente va a repartir los 2100 m²');
    http.expectNone('http://localhost:8000/proyectos/p-1/agente');
  });

  it('collects a product written by hand and explains a too short name', async () => {
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    const agregar = Array.from(
      html.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((boton) => boton.textContent?.trim() === 'Agregar')!;
    agregar.click();
    await harness.fixture.whenStable();
    expect(html.textContent).toContain('Escribí al menos 2 letras del producto');

    const campo = html.querySelector('#nuevo-producto') as HTMLInputElement;
    campo.value = 'yuca';
    campo.dispatchEvent(new Event('input', { bubbles: true }));
    await harness.fixture.whenStable();
    agregar.click();
    await harness.fixture.whenStable();

    expect(html.querySelectorAll('article').length).toBe(1);
    expect(html.textContent).toContain('yuca');
    expect(html.textContent).toContain('Nuevo · se investiga');
  });

  // La persistencia se prueba en wizard-draft.store.spec.ts: el harness del router
  // sólo permite un montaje por test y ahí no hace falta duplicarlo.

  it('hands the step over to the irrigation route', async () => {
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    const aSistema = Array.from(
      html.querySelectorAll('a') as NodeListOf<HTMLAnchorElement>,
    ).find((enlace) => enlace.textContent?.includes('A Sistema'))!;

    expect(aSistema.getAttribute('href')).toBe('/proyectos/p-1/riego');
  });
});
