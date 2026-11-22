import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { WizardDraftStore } from '../../wizard/state/wizard-draft.store';
import { RiegoPage } from '../riego.page';

const PROYECTO = {
  id: 'p-1',
  nombre: 'Los Olivos',
  zona: 'Oruro',
  unidad: 'metric',
  estado: 'en_progreso',
  paso_actual: 3,
  ultimo_paso_completado: 2,
  version: 3,
  corrida_actual_id: null,
  creado_en: '2026-11-21T12:00:00',
  actualizado_en: '2026-11-21T12:30:00',
};

const TERRENO = {
  area_m2: 3200,
  fuente_agua: 'pozo',
  caudal_disponible_m3h: 1.8,
  caudal_efectivo_m3h: 1.8,
};

describe('RiegoPage (paso 3: sólo restricciones)', () => {
  let http: HttpTestingController;
  let borrador: WizardDraftStore;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'proyectos/:proyectoId/riego', component: RiegoPage },
          { path: 'proyectos/:proyectoId/cultivos', component: RiegoPage },
        ]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    borrador = TestBed.inject(WizardDraftStore);
  });

  afterEach(() => http.verify());

  async function montar(caudalEfectivo = 1.8, fuente: 'pozo' | 'pila' | 'tanque' | 'cisterna' = 'pozo') {
    const harness = await RouterTestingHarness.create('/proyectos/p-1/riego');
    http.expectOne('http://localhost:8000/proyectos/p-1').flush(PROYECTO);
    http
      .expectOne('http://localhost:8000/proyectos/p-1/terreno')
      .flush({ ...TERRENO, fuente_agua: fuente, caudal_efectivo_m3h: caudalEfectivo });
    await harness.fixture.whenStable();
    return harness;
  }

  function escribirPresupuesto(html: HTMLElement, valor: string) {
    const campo = html.querySelector('#presupuesto') as HTMLInputElement;
    campo.value = valor;
    campo.dispatchEvent(new Event('input', { bubbles: true }));
  }

  it('shows the water source of step 1 and the default restrictions', async () => {
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    expect(html.textContent).toContain('Los Olivos');
    // La fuente y el caudal vienen del paso 1: no se vuelven a pedir.
    expect(html.textContent).toContain('Pozo');
    expect(html.textContent).toContain('1.8 m³/h');
    expect(html.textContent).toContain('Red eléctrica');
    expect(html.textContent).toContain('No tiene');
    expect(html.textContent).toContain('Sin presupuesto');
    // El paso 3 no calcula ni llama al agente.
    expect(html.textContent).toContain('Este paso no consulta al agente');
    http.expectNone('http://localhost:8000/proyectos/p-1/agente');
  });

  it('collects energy, existing tank and budget without writing', async () => {
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    (html.querySelector('[data-energia="solar"]') as HTMLButtonElement).click();
    const tanque = html.querySelector('#tanque') as HTMLSelectElement;
    tanque.value = '5000';
    tanque.dispatchEvent(new Event('change', { bubbles: true }));
    escribirPresupuesto(html, '1500');
    await harness.fixture.whenStable();

    expect(html.textContent).toContain('Solar');
    expect(html.textContent).toContain('5000 L');
    expect(html.textContent).toContain('1500 Bs');
    expect(borrador.aPayload().restricciones).toEqual({
      energia: 'solar',
      tanque_l: 5000,
      presupuesto_bs: 1500,
    });
    http.expectNone('http://localhost:8000/proyectos/p-1/agente');
  });

  it('warns about a budget below the floor and keeps it out of the payload', async () => {
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    escribirPresupuesto(html, '50');
    await harness.fixture.whenStable();

    expect(html.textContent).toContain(
      'El mínimo para un sistema de riego es 100 Bs; ese monto no se manda al agente.',
    );
    expect(html.textContent).toContain('No se manda (bajo el mínimo)');
    expect(borrador.aPayload().restricciones.presupuesto_bs).toBeNull();
  });

  it('explains what the budget is for when it is left empty', async () => {
    const harness = await montar();
    const html = harness.routeNativeElement as HTMLElement;

    expect(html.textContent).toContain(
      'Si ponés un presupuesto, el agente elige los materiales dentro de ese presupuesto.',
    );
    expect(borrador.aPayload().restricciones.presupuesto_bs).toBeNull();
  });

  it('warns when the terrain has no effective flow instead of blocking', async () => {
    const harness = await montar(0);
    const html = harness.routeNativeElement as HTMLElement;

    expect(html.textContent).toContain('El terreno no tiene caudal informado');
    // Avisa, no bloquea: el formulario sigue disponible.
    expect((html.querySelector('#presupuesto') as HTMLInputElement).disabled).toBe(false);
  });

  it('asks for the capacity of the tank the terrain already declares', async () => {
    const harness = await montar(1.8, 'tanque');
    const html = harness.routeNativeElement as HTMLElement;
    const tanque = html.querySelector('#tanque') as HTMLSelectElement;
    const etiquetas = Array.from(tanque.options).map((opcion) => opcion.textContent?.trim());

    // La fuente ya es un depósito: preguntar "¿ya tenés tanque?" sería redundante.
    expect(html.textContent).toContain('Capacidad de tu tanque');
    expect(html.textContent).not.toContain('¿Ya tenés tanque?');
    expect(html.textContent).toContain('El paso 1 ya declara tanque como fuente');
    expect(etiquetas).toEqual(['2.500 L', '5.000 L', '10.000 L', 'No sé (lo estima el agente)']);
    expect(html.textContent).toContain('Sin dato');
  });

  it('asks whether a tank exists when the source is a tap', async () => {
    const harness = await montar(1.8, 'pila');
    const html = harness.routeNativeElement as HTMLElement;
    const tanque = html.querySelector('#tanque') as HTMLSelectElement;

    expect(html.textContent).toContain('¿Ya tenés tanque?');
    expect(html.textContent).toContain('El tanque es el depósito de cabecera, no la fuente');
    expect(Array.from(tanque.options).map((opcion) => opcion.textContent?.trim())).toEqual([
      'No tiene',
      '2.500 L',
      '5.000 L',
      '10.000 L',
    ]);
    expect(html.textContent).toContain('No tiene');
  });
});
