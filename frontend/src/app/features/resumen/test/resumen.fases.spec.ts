import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  TestRequest,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { vi } from 'vitest';
import { PROGRESO_RELOJ, PROGRESO_TICK_MS } from '../components/progreso-corrida/progreso-corrida';
import { ResumenPage } from '../resumen.page';
import { RESUMEN_POLL_MS } from '../state/resumen.store';

const API = 'http://localhost:8000';
const BASE = `${API}/proyectos`;
const CLAVE_BORRADOR = 'agroplan.borrador';
const CORRIDA_URL = `${BASE}/p-1/agente/corridas/c-1`;

const PROYECTO = {
  id: 'p-1',
  nombre: 'Los Olivos',
  zona: 'Oruro',
  unidad: 'metric',
  estado: 'en_progreso',
  paso_actual: 3,
  ultimo_paso_completado: 3,
  version: 4,
  corrida_actual_id: null,
  creado_en: '2026-11-21T12:00:00',
  actualizado_en: '2026-11-21T12:30:00',
};

const TERRENO = {
  nombre_parcela: 'La Hoyada',
  area_m2: 3200,
  caudal_disponible_m3h: 1.8,
  caudal_efectivo_m3h: 1.8,
  suelo_codigo: 'franco_arenado',
  fuente_agua: 'pozo',
  geometria: { vertices: [] },
};

const CORRIDA = {
  id: 'c-1',
  proyecto_id: 'p-1',
  estado: 'corriendo',
  modelo: 'test',
  motor_version: '1',
  prompt_version: '1',
  intake_hash: 'h-1',
  tokens_entrada: null,
  tokens_salida: null,
  duracion_ms: null,
  error_detalle: null,
  iniciado_en: '2026-11-21T12:00:00',
  terminado_en: null,
  entrada: {},
  salida: null,
  fuentes: [],
  recomendaciones: [],
};

describe('ResumenPage (progreso real del agente: S2, S3, S4)', () => {
  let http: HttpTestingController;
  /** Reloj del cronómetro: el test fija el instante, nunca el reloj real (S4). */
  let reloj: { ahora: number };

  beforeEach(async () => {
    // Arranca unos minutos en el pasado para que las fases ya tengan historia.
    reloj = { ahora: Date.now() };
    const relojActual = () => reloj.ahora;
    localStorage.clear();
    await TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'proyectos/:proyectoId/resultado', component: ResumenPage },
          { path: 'proyectos/:proyectoId/cultivos', component: ResumenPage },
          { path: 'proyectos/:proyectoId/riego', component: ResumenPage },
        ]),
        provideHttpClient(),
        provideHttpClientTesting(),
        // El sondeo no encima consultas: con un intervalo largo sólo llega la primera,
        // que es la que trae la fase, y el test no depende de esperas reales.
        { provide: RESUMEN_POLL_MS, useValue: 600000 },
        { provide: PROGRESO_RELOJ, useValue: relojActual },
        // El cronómetro se refresca enseguida: el test no espera segundos reales.
        { provide: PROGRESO_TICK_MS, useValue: 5 },
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    vi.restoreAllMocks();
  });

  function sembrarBorrador() {
    localStorage.setItem(
      CLAVE_BORRADOR,
      JSON.stringify({
        proyectoId: 'p-1',
        productos: [{ codigo: 'papa', texto: 'papa', etiqueta: 'Papa', color: '#8D6E63' }],
        siembra: '2026-11-21',
        restricciones: { energia: 'solar', tanque_l: 5000, presupuesto_bs: 1500 },
      }),
    );
  }

  async function montar() {
    const harness = await RouterTestingHarness.create('/proyectos/p-1/resultado');
    http.expectOne(`${BASE}/p-1`).flush(PROYECTO);
    http.expectOne(`${BASE}/p-1/terreno`).flush(TERRENO);
    http.expectOne(`${API}/catalogos/suelos`).flush([]);
    http.expectOne(`${API}/catalogos/cultivos`).flush([]);
    http
      .expectOne(`${BASE}/p-1/resultado`)
      .flush({ detail: 'sin red' }, { status: 404, statusText: 'Not Found' });
    await harness.fixture.whenStable();
    return harness;
  }

  async function esperarConsulta(url: string): Promise<TestRequest> {
    const limite = Date.now() + 3000;
    for (;;) {
      const pendientes = http.match(url);
      if (pendientes.length > 0) return pendientes[pendientes.length - 1];
      if (Date.now() > limite) throw new Error(`No llegó la consulta a ${url}`);
      await new Promise((resolver) => setTimeout(resolver, 5));
    }
  }

  /** Lleva la pantalla a `generando` y responde la primera consulta con la fase dada. */
  async function generando(
    harness: RouterTestingHarness,
    detalle: Record<string, unknown>,
  ): Promise<HTMLElement> {
    const html = harness.routeNativeElement as HTMLElement;
    const generar = Array.from(html.querySelectorAll('button')).find(
      (candidato) => candidato.textContent?.trim() === 'Generar informe',
    );
    generar!.click();
    await harness.fixture.whenStable();
    http
      .expectOne(`${BASE}/p-1/agente`)
      .flush({ corrida_id: 'c-1', estado: 'pendiente', intake_hash: 'h-1' });

    const consulta = await esperarConsulta(CORRIDA_URL);
    consulta.flush({ ...CORRIDA, ...detalle });
    await harness.fixture.whenStable();
    return html;
  }

  function fase(html: HTMLElement, nombre: string): HTMLElement {
    const encontrada = html.querySelector(`[data-fase="${nombre}"]`) as HTMLElement | null;
    if (encontrada === null) throw new Error(`No se ve la fase "${nombre}"`);
    return encontrada;
  }

  function haceSegundos(segundos: number): string {
    return new Date(reloj.ahora - segundos * 1000).toISOString();
  }

  /** Mueve el reloj del cronómetro y espera el refresco real de la pantalla. */
  async function avanzar(harness: RouterTestingHarness, segundos: number): Promise<void> {
    reloj.ahora += segundos * 1000;
    await new Promise((resolver) => setTimeout(resolver, 30));
    await harness.fixture.whenStable();
  }

  it('marca las fases cumplidas con check y la actual con su indicador animado (S2)', async () => {
    sembrarBorrador();
    const harness = await montar();
    const html = await generando(harness, {
      fase: 'modelo',
      fase_desde: haceSegundos(3),
    });

    expect(fase(html, 'contexto').getAttribute('data-estado-fase')).toBe('cumplida');
    expect(fase(html, 'contexto').querySelector('[data-icono="check"]')).not.toBeNull();

    expect(fase(html, 'modelo').getAttribute('data-estado-fase')).toBe('actual');
    expect(fase(html, 'modelo').querySelector('[data-icono="actual"]')).not.toBeNull();
    expect(fase(html, 'modelo').querySelector('ng-icon')?.classList.contains('animate-spin')).toBe(
      true,
    );

    for (const pendiente of ['validacion', 'precios', 'red', 'listo']) {
      expect(fase(html, pendiente).getAttribute('data-estado-fase')).toBe('pendiente');
      expect(fase(html, pendiente).querySelector('[data-icono="pendiente"]')).not.toBeNull();
    }

    // Con fase, la espera muestra el avance real en vez del spinner mudo.
    expect(html.querySelector('[data-progreso-corrida]')).not.toBeNull();
    expect(html.querySelector('ng-icon.animate-spin[data-spinner-generico]')).toBeNull();

    harness.fixture.destroy();
  });

  it('el cronómetro cuenta desde fase_desde del servidor y avanza solo (S2, S4)', async () => {
    sembrarBorrador();
    const harness = await montar();
    const html = await generando(harness, {
      fase: 'modelo',
      fase_desde: haceSegundos(3),
    });

    // El conteo arranca en el instante que el servidor marcó, no en el render.
    expect(html.querySelector('[data-cronometro]')?.textContent?.trim()).toBe('0:03');

    await avanzar(harness, 4);
    expect(html.querySelector('[data-cronometro]')?.textContent?.trim()).toBe('0:07');

    // Recargar la pantalla no reinicia ni infla el conteo: sigue saliendo de fase_desde.
    await avanzar(harness, 56);
    expect(html.querySelector('[data-cronometro]')?.textContent?.trim()).toBe('1:03');

    harness.fixture.destroy();
  });

  it('no muestra un cronómetro negativo si el reloj del cliente está adelantado (S4)', async () => {
    sembrarBorrador();
    const harness = await montar();
    const html = await generando(harness, {
      fase: 'contexto',
      fase_desde: new Date(reloj.ahora + 90_000).toISOString(),
    });

    expect(html.querySelector('[data-cronometro]')?.textContent?.trim()).toBe('0:00');

    harness.fixture.destroy();
  });

  it('pasados 20 s en la fase del modelo explica que la corrida sigue viva (S2)', async () => {
    sembrarBorrador();
    const harness = await montar();
    const html = await generando(harness, {
      fase: 'modelo',
      fase_desde: haceSegundos(5),
    });

    // A los 14 s todavía no hace falta explicar nada.
    await avanzar(harness, 9);
    expect(html.querySelector('[data-espera-larga]')).toBeNull();

    // Pasados 20 s en la fase del modelo se explica la espera real.
    await avanzar(harness, 7);
    const aviso = html.querySelector('[data-espera-larga]') as HTMLElement | null;
    expect(aviso).not.toBeNull();
    expect(aviso?.textContent).toContain('uno o dos minutos');
    expect(aviso?.textContent).toContain('sigue viva');
    expect(aviso?.textContent).toContain('90 segundos');

    harness.fixture.destroy();
  });

  it('el error dice en qué fase quedó la corrida, con el detalle del backend (S3)', async () => {
    sembrarBorrador();
    const harness = await montar();
    const html = await generando(harness, {
      estado: 'error',
      fase: 'validacion',
      fase_desde: haceSegundos(2),
      error_detalle: 'La propuesta no tiene bloques de cultivo',
    });

    expect(html.textContent).toContain('El informe no se pudo generar');
    const error = html.querySelector('[data-error-informe]') as HTMLElement;
    expect(error.textContent).toContain('falló mientras validaba la propuesta');
    expect(error.textContent).toContain('La propuesta no tiene bloques de cultivo');

    harness.fixture.destroy();
  });

  it('una corrida sin fase mantiene la espera genérica sin romper la pantalla (S2)', async () => {
    sembrarBorrador();
    const harness = await montar();
    const html = await generando(harness, { fase: null, fase_desde: null });

    expect(html.textContent).toContain('El agente está armando el informe');
    expect(html.textContent).toContain('Esto puede tardar un par de minutos');
    expect(html.querySelector('[data-progreso-corrida]')).toBeNull();
    expect(html.querySelector('[data-cronometro]')).toBeNull();
    expect(html.querySelector('ng-icon[data-spinner-generico]')).not.toBeNull();

    harness.fixture.destroy();
  });
});
