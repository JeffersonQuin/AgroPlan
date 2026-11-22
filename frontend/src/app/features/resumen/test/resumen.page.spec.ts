import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  TestRequest,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { ResumenPage } from '../resumen.page';
import { RESUMEN_POLL_MS } from '../state/resumen.store';

const API = 'http://localhost:8000';
const BASE = `${API}/proyectos`;
const CLAVE_BORRADOR = 'agroplan.borrador';

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
  geometria: {
    vertices: [
      { x: 0, y: 0 },
      { x: 40, y: 0 },
      { x: 40, y: 80 },
      { x: 0, y: 80 },
    ],
  },
};

const SUELOS = [
  {
    codigo: 'franco_arenado',
    nombre: 'Franco arenado',
    infiltracion_mm_h: 18,
    retencion_agua_mm_m: 110,
  },
];

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
    imagen_url: 'https://commons.example/papa.jpg',
    imagen_credito: 'Wikimedia Commons · CC BY-SA 4.0',
  },
];

const RESULTADO = {
  proyecto_id: 'p-1',
  nombre: 'Los Olivos',
  estado: 'completado',
  diseno: {
    bloques: [],
    sistema: {},
    sectores: [],
    red: { nodos: [], tramos: [], emisores: [] },
    computo: { tuberia_m: 0, goteros_u: 0, valvulas_u: 0 },
    advertencias: [],
    cifras: {},
    cifras_agente: null,
    eficiencia_pct: null,
    calendario: [],
    materiales: [],
    presupuesto_bs: null,
    costo_total_bs: null,
    presupuesto_excedido: null,
    recomendaciones: [],
    fuentes: [],
    ajustes: [],
  },
  advertencias: [
    {
      codigo: 'presion_ajustada',
      mensaje: 'El motor ajustó la presión de trabajo a 1.5 bar.',
      bloqueante: false,
      campo: null,
    },
  ],
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

describe('ResumenPage (paso 4: flujo del informe)', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
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
        // El sondeo real espera 2 s; en el test no hace falta esperarlos.
        { provide: RESUMEN_POLL_MS, useValue: 5 },
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  /** Borrador del paso 2 y restricciones del paso 3, como los deja el wizard. */
  function sembrarBorrador(
    restricciones = { energia: 'solar', tanque_l: 5000, presupuesto_bs: 1500 },
  ) {
    localStorage.setItem(
      CLAVE_BORRADOR,
      JSON.stringify({
        proyectoId: 'p-1',
        productos: [{ codigo: 'papa', texto: 'papa', etiqueta: 'Papa', color: '#8D6E63' }],
        siembra: '2026-11-21',
        restricciones,
      }),
    );
  }

  async function montar(resultado: Record<string, unknown> | null = null) {
    const harness = await RouterTestingHarness.create('/proyectos/p-1/resultado');
    http.expectOne(`${BASE}/p-1`).flush(PROYECTO);
    http.expectOne(`${BASE}/p-1/terreno`).flush(TERRENO);
    http.expectOne(`${API}/catalogos/suelos`).flush(SUELOS);
    http.expectOne(`${API}/catalogos/cultivos`).flush(CATALOGO);
    const informe = http.expectOne(`${BASE}/p-1/resultado`);
    if (resultado === null) {
      // 404 es el caso normal: la red todavía no se generó.
      informe.flush(
        { detail: 'La red de riego todavía no fue generada' },
        { status: 404, statusText: 'Not Found' },
      );
    } else {
      informe.flush(resultado);
    }
    await harness.fixture.whenStable();
    return harness;
  }

  /**
   * Espera la próxima consulta de la corrida.
   *
   * El sondeo usa `timer`, así que el test espera el pedido real en vez de avanzar
   * relojes: así también se prueba que el intervalo no se encima.
   */
  async function esperarConsulta(url: string): Promise<TestRequest> {
    const limite = Date.now() + 3000;
    for (;;) {
      const pendientes = http.match(url);
      if (pendientes.length > 0) return pendientes[pendientes.length - 1];
      if (Date.now() > limite) throw new Error(`No llegó la consulta a ${url}`);
      await new Promise((resolver) => setTimeout(resolver, 5));
    }
  }

  function boton(html: HTMLElement, texto: string): HTMLButtonElement {
    const encontrado = Array.from(html.querySelectorAll('button')).find(
      (candidato) => candidato.textContent?.trim() === texto,
    );
    if (encontrado === undefined) throw new Error(`No hay botón "${texto}"`);
    return encontrado;
  }

  it('muestra el resumen completo del borrador en el modal antes de generar', async () => {
    sembrarBorrador();
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;
    const modal = html.querySelector('[data-modal-resumen]') as HTMLElement;

    expect(modal).not.toBeNull();
    expect(modal.textContent).toContain('Revisá el resumen antes de generar');

    // Terreno del paso 1.
    expect(modal.querySelector('[data-terreno-nombre]')?.textContent).toContain('La Hoyada');
    expect(modal.querySelector('[data-terreno-area]')?.textContent).toContain('3200 m²');
    expect(modal.querySelector('[data-terreno-suelo]')?.textContent).toContain('Franco arenado');
    expect(modal.querySelector('[data-terreno-fuente]')?.textContent).toContain('Pozo');
    expect(modal.querySelector('[data-terreno-caudal]')?.textContent).toContain('1.8 m³/h');

    // Productos con la imagen de su ficha curada.
    const producto = modal.querySelector('[data-producto]') as HTMLElement;
    expect(producto.textContent).toContain('Papa');
    expect(producto.querySelector('img')?.getAttribute('src')).toBe(
      'https://commons.example/papa.jpg',
    );
    expect(producto.textContent).toContain('Wikimedia Commons');

    // Siembra y restricciones del paso 3.
    expect(modal.querySelector('[data-siembra]')?.textContent).toContain('2026-11-21');
    expect(modal.querySelector('[data-restriccion-energia]')?.textContent).toContain('Solar');
    expect(modal.querySelector('[data-restriccion-tanque]')?.textContent).toContain('5000 L');
    expect(modal.querySelector('[data-restriccion-presupuesto]')?.textContent).toContain('1500 Bs');

    expect(boton(modal, 'Generar informe').disabled).toBe(false);
    // Nada se dispara hasta que el usuario confirme.
    expect(http.match(`${BASE}/p-1/agente`).length).toBe(0);
  });

  it('no dispara el agente hasta que el usuario confirma el modal', async () => {
    sembrarBorrador();
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    expect(html.textContent).toContain('Generar informe');
    http.expectNone(`${BASE}/p-1/agente`);

    boton(html, 'Generar informe').click();
    await harness.fixture.whenStable();

    const disparo = http.expectOne(`${BASE}/p-1/agente`);
    expect(disparo.request.method).toBe('POST');
    expect(disparo.request.body).toEqual({
      productos: [{ cultivo_codigo: 'papa' }],
      siembra: '2026-11-21',
      restricciones: { energia: 'solar', tanque_l: 5000, presupuesto_bs: 1500 },
    });
    disparo.flush({ corrida_id: 'c-1', estado: 'pendiente', intake_hash: 'h-1' });
    await harness.fixture.whenStable();

    // La corrida ya está en curso: se ve el progreso y no hay segundo disparo.
    expect(html.textContent).toContain('El agente está armando el informe');
    expect(http.match(`${BASE}/p-1/agente`).length).toBe(0);

    // Se destruye la página para cancelar el sondeo todavía en curso.
    harness.fixture.destroy();
  });

  it('sondea la corrida hasta ok, la aplica y muestra el informe una sola vez', async () => {
    sembrarBorrador();
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    boton(html, 'Generar informe').click();
    await harness.fixture.whenStable();
    http
      .expectOne(`${BASE}/p-1/agente`)
      .flush({ corrida_id: 'c-1', estado: 'pendiente', intake_hash: 'h-1' });

    const primera = await esperarConsulta(`${BASE}/p-1/agente/corridas/c-1`);
    primera.flush({ ...CORRIDA, estado: 'corriendo' });
    await harness.fixture.whenStable();
    expect(html.textContent).toContain('El agente está armando el informe');

    const segunda = await esperarConsulta(`${BASE}/p-1/agente/corridas/c-1`);
    segunda.flush({ ...CORRIDA, estado: 'ok' });
    await harness.fixture.whenStable();

    const aplicar = await esperarConsulta(`${BASE}/p-1/agente/corridas/c-1/aplicar`);
    expect(aplicar.request.method).toBe('POST');
    aplicar.flush(RESULTADO);
    await harness.fixture.whenStable();

    expect(html.querySelector('[data-informe]')).not.toBeNull();
    expect(html.textContent).toContain('Informe generado');
    expect(html.textContent).toContain('El motor ajustó la presión de trabajo a 1.5 bar.');

    const regenerar = boton(html, 'Regenerar');
    expect(regenerar.disabled).toBe(true);
    expect(regenerar.title).toBe('Plan premium');

    // Una sola generación: ni otro disparo ni más sondeos.
    expect(http.match(`${BASE}/p-1/agente`).length).toBe(0);
    expect(http.match(`${BASE}/p-1/agente/corridas/c-1`).length).toBe(0);
  });

  it('muestra el error del backend y reintenta el disparo', async () => {
    sembrarBorrador();
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    boton(html, 'Generar informe').click();
    await harness.fixture.whenStable();
    http
      .expectOne(`${BASE}/p-1/agente`)
      .flush({ corrida_id: 'c-1', estado: 'pendiente', intake_hash: 'h-1' });

    const consulta = await esperarConsulta(`${BASE}/p-1/agente/corridas/c-1`);
    consulta.flush({
      ...CORRIDA,
      estado: 'error',
      error_detalle: 'El agente no devolvió una propuesta válida',
    });
    await harness.fixture.whenStable();

    expect(html.textContent).toContain('El informe no se pudo generar');
    expect(html.querySelector('[data-error-informe]')?.textContent).toContain(
      'El agente no devolvió una propuesta válida',
    );

    boton(html, 'Reintentar').click();
    await harness.fixture.whenStable();

    const reintento = http.expectOne(`${BASE}/p-1/agente`);
    expect(reintento.request.method).toBe('POST');
    reintento.flush({ corrida_id: 'c-2', estado: 'pendiente', intake_hash: 'h-1' });

    // Se destruye la página para cancelar el sondeo todavía en curso.
    harness.fixture.destroy();
  });

  it('muestra el informe ya generado sin volver a llamar al agente', async () => {
    sembrarBorrador();
    const harness = await montar(RESULTADO);
    const html = harness.routeNativeElement as HTMLElement;

    expect(html.querySelector('[data-informe]')).not.toBeNull();
    expect(html.textContent).toContain('Informe generado');
    expect(html.textContent).toContain('Cómputo listo');
    expect(html.textContent).toContain('El motor ajustó la presión de trabajo a 1.5 bar.');

    const regenerar = boton(html, 'Regenerar');
    expect(regenerar.disabled).toBe(true);
    expect(regenerar.title).toBe('Plan premium');

    http.expectNone(`${BASE}/p-1/agente`);
    expect(http.match(`${BASE}/p-1/agente/corridas/c-1`).length).toBe(0);
  });

  it('explica que falta el borrador y lleva al paso 2, sin dejar generar', async () => {
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    expect(html.textContent).toContain('Todavía no hay productos en el borrador');
    expect(html.textContent).toContain('Ir a Cultivos');
    const irACultivos = Array.from(
      html.querySelectorAll('a') as NodeListOf<HTMLAnchorElement>,
    ).find((enlace) => enlace.textContent?.includes('Ir a Cultivos'));
    expect(irACultivos?.getAttribute('href')).toBe('/proyectos/p-1/cultivos');
    expect(html.textContent).not.toContain('Generar informe');
    http.expectNone(`${BASE}/p-1/agente`);
  });
});
