import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { CultivosPage } from '../cultivos.page';

const PROYECTO = {
  id: 'p-1',
  nombre: 'Los Olivos',
  zona: 'Cuyo',
  unidad: 'metric',
  estado: 'en_progreso',
  paso_actual: 2,
  ultimo_paso_completado: 1,
  version: 2,
  corrida_actual_id: null,
  creado_en: '2026-11-21T12:00:00',
  actualizado_en: '2026-11-21T12:30:00',
};

const BLOQUE = {
  id: 'b-1',
  cultivo_codigo: 'papa',
  etiqueta: 'Zona A',
  area_m2: 140,
  poligono: { anillo: [[0, 0], [10, 0], [10, 14], [0, 14]] },
  siembra: null,
  cosecha: null,
  demanda_l_m2_dia: 2,
  orden: 1,
  origen: 'porcentaje',
  porcentaje: 70,
  demanda_total_l_dia: 280,
  ciclo_dias: 120,
  kc: 1.15,
  dias_a_cosecha: null,
  aptitud_suelo: { veredicto: 'apto', motivo: 'Suelo equilibrado.', fuente: 'Ficha' },
  advertencias: [],
};

const BALANCE = {
  terreno_m2: 200,
  asignado_m2: 140,
  disponible_m2: 60,
  estado: 'ajustado',
  demanda_total_l_dia: 280,
  demanda_prom_l_m2_dia: 2,
  calendario: [],
  solapes: [],
  alertas: [],
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

describe('CultivosPage', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
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

  async function montar(bloques: unknown[] = [BLOQUE]) {
    const harness = await RouterTestingHarness.create('/proyectos/p-1/cultivos');
    http.expectOne('http://localhost:8000/proyectos/p-1').flush(PROYECTO);
    http.expectOne('http://localhost:8000/proyectos/p-1/terreno').flush({
      area_m2: 200,
      caudal_efectivo_m3h: 3,
      suelo_codigo: 'franco',
      geometria: {
        vertices: [
          { x: 0, y: 0 },
          { x: 10, y: 0 },
          { x: 10, y: 20 },
          { x: 0, y: 20 },
        ],
      },
    });
    http.expectOne('http://localhost:8000/proyectos/p-1/cultivos').flush(bloques);
    http.expectOne('http://localhost:8000/proyectos/p-1/cultivos/balance').flush(BALANCE);
    http.expectOne('http://localhost:8000/catalogos/cultivos').flush(CATALOGO);
    await harness.fixture.whenStable();
    return harness;
  }

  it('renders the project, the configured crops and the balance', async () => {
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    expect(html.textContent).toContain('Los Olivos');
    expect(html.textContent).toContain('Cultivos configurados (1)');
    expect(html.textContent).toContain('Zona A');
    expect(html.textContent).toContain('140 m²');
    expect(html.textContent).toContain('280 L/día');
    expect(html.textContent).toContain('Suelo: apto');
    expect(html.textContent).toContain('Capacidad hidráulica de referencia');
    expect(html.textContent).toContain('3 m³/h');
  });

  it('shows the step-1 terrain as the default distribution', async () => {
    const harness = await montar([]);
    const html = harness.routeNativeElement as HTMLElement;

    expect(html.textContent).toContain('Terreno del paso 1');
    expect(html.textContent).toContain(
      'Agregá productos y generá la distribución con el agente',
    );
    const generar = Array.from(
      html.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((boton) => boton.textContent?.includes('Generar distribución'))!;
    expect(generar.disabled).toBe(true);
  });

  it('adds a product and asks for confirmation before generating', async () => {
    // Sin distribución previa: el paso 2 está en modo "elegir productos".
    const harness = await montar([]);
    const html = harness.routeNativeElement as HTMLElement;

    const agregar = html.querySelector(
      'button[aria-label="Agregar producto del catálogo"]',
    ) as HTMLButtonElement;
    agregar.click();
    await harness.fixture.whenStable();

    expect(html.textContent).toContain('Productos elegidos (1)');
    expect(html.textContent).toContain('Lechuga');

    const generar = Array.from(
      html.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((boton) => boton.textContent?.includes('Generar distribución'))!;
    expect(generar.disabled).toBe(false);

    generar.click();
    await harness.fixture.whenStable();

    expect(html.textContent).toContain('¿Generar la distribución?');
    expect(html.textContent).toContain('una sola vez');
    expect(html.textContent).toContain('La siembra queda para el');
  });
});
