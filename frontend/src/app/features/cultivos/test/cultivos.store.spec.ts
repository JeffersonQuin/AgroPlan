import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { BalanceApi, BloqueApi, CultivoCatalogoApi } from '../models/cultivos.model';
import { CultivosStore } from '../state/cultivos.store';

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

const TERRENO = {
  area_m2: 200,
  caudal_efectivo_m3h: 3,
  suelo_codigo: 'franco',
};

const PAPA: BloqueApi = {
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

const BALANCE: BalanceApi = {
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

const CATALOGO: CultivoCatalogoApi[] = [
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
    meses_siembra: [3, 9],
    activo: true,
  },
  {
    codigo: 'viejo',
    nombre: 'Inactivo',
    icono: 'I',
    color: '#000000',
    demanda_agua_l_m2_dia: 1,
    ciclo_dias: 90,
    kc: null,
    densidad_plantas_m2: null,
    profundidad_raiz_cm: null,
    meses_siembra: null,
    activo: false,
  },
];

describe('CultivosStore', () => {
  let store: CultivosStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(CultivosStore);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function cargar(bloques: BloqueApi[] = [PAPA]): void {
    store.cargar('p-1');
    http.expectOne('http://localhost:8000/proyectos/p-1').flush(PROYECTO);
    http.expectOne('http://localhost:8000/proyectos/p-1/terreno').flush(TERRENO);
    http.expectOne('http://localhost:8000/proyectos/p-1/cultivos').flush(bloques);
    http.expectOne('http://localhost:8000/proyectos/p-1/cultivos/balance').flush(BALANCE);
    http.expectOne('http://localhost:8000/catalogos/cultivos').flush(CATALOGO);
  }

  it('loads the project, the terrain reference, the blocks and the panel', () => {
    cargar();

    expect(store.nombreProyecto()).toBe('Los Olivos');
    expect(store.areaM2()).toBe(200);
    expect(store.caudalM3h()).toBe(3);
    expect(store.sueloCodigo()).toBe('franco');
    expect(store.bloques().length).toBe(1);
    expect(store.estado()).toBe('listo');
    expect(store.estadoGuardadoLabel()).toBe('Guardado');
    expect(store.asignadoPct()).toBe(70);
    expect(store.estadoBalance()).toBe('ajustado');
  });

  it('only offers the active catalogue, with its agronomic data', () => {
    cargar();

    expect(store.opcionesCultivo()).toEqual([
      { value: 'papa', label: 'Papa', demanda: 2, ciclo: 120, kc: 1.15, color: '#8D6E63' },
    ]);
    expect(store.cultivoSeleccionado()?.value).toBe('papa');
  });

  it('adds a crop by percentage and refreshes the panel with the answer', () => {
    cargar();

    store.agregar('papa', 30)!.subscribe();

    const peticion = http.expectOne('http://localhost:8000/proyectos/p-1/cultivos');
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body).toEqual({
      cultivo_codigo: 'papa',
      etiqueta: '2',
      modo: 'porcentaje',
      porcentaje: 30,
    });
    peticion.flush({
      bloque: { ...PAPA, id: 'b-2', porcentaje: 30, area_m2: 60 },
      balance: { ...BALANCE, asignado_m2: 200, disponible_m2: 0, estado: 'correcto' },
      advertencias: [],
    });

    expect(store.bloques().length).toBe(2);
    expect(store.bloques().map((bloque) => bloque.orden)).toEqual([1, 1]);
    expect(store.estadoBalance()).toBe('correcto');
    expect(store.asignadoPct()).toBe(100);
    expect(store.estado()).toBe('listo');
  });

  it('surfaces the backend detail when the crop does not fit', () => {
    cargar();

    store.agregar('papa', 80)!.subscribe({ error: () => undefined });
    http
      .expectOne('http://localhost:8000/proyectos/p-1/cultivos')
      .flush({ detail: 'La suma de porcentajes supera el 100%' }, { status: 422, statusText: 'Unprocessable' });

    expect(store.estado()).toBe('error');
    expect(store.error()).toBe('La suma de porcentajes supera el 100%');
  });

  it('sends the product list and the sowing date to the agent', () => {
    cargar([]);
    store.agregarProducto('papa', '');
    store.agregarProducto(null, 'yuca');
    store.setSiembra('2026-11-20');

    expect(store.puedeGenerar()).toBe(true);
    store.generar();

    const peticion = http.expectOne('http://localhost:8000/proyectos/p-1/agente');
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body).toEqual({
      productos: [{ cultivo_codigo: 'papa' }, { producto_texto: 'yuca' }],
      siembra: '2026-11-20',
    });
    expect(peticion.request.body.productos.length).toBe(2);
    expect(store.generando()).toBe(true);
  });

  it('surfaces the agent failure without leaving the spinner on', () => {
    cargar([]);
    store.agregarProducto('papa', '');
    store.generar();

    http
      .expectOne('http://localhost:8000/proyectos/p-1/agente')
      .flush({ detail: 'La corrida ya está aplicada' }, { status: 409, statusText: 'Conflict' });

    expect(store.generando()).toBe(false);
    expect(store.error()).toBe('La corrida ya está aplicada');
    expect(store.puedeGenerar()).toBe(true);
  });

  it('removes a block and asks for the new balance', () => {
    cargar();

    store.eliminar('b-1')!.subscribe();

    http.expectOne('http://localhost:8000/proyectos/p-1/cultivos/b-1').flush(null);
    expect(store.bloques()).toEqual([]);

    http
      .expectOne('http://localhost:8000/proyectos/p-1/cultivos/balance')
      .flush({ ...BALANCE, asignado_m2: 0, disponible_m2: 200, estado: 'ajustado' });

    expect(store.estado()).toBe('listo');
    expect(store.asignadoPct()).toBe(0);
  });

  it('reports a loading failure with a readable message', () => {
    store.cargar('p-1');
    // Se resuelven las cuatro consultas tolerantes antes de hacer fallar el proyecto:
    // así el forkJoin no cancela nada y no quedan peticiones abiertas.
    http.expectOne('http://localhost:8000/proyectos/p-1/terreno').flush(TERRENO);
    http.expectOne('http://localhost:8000/proyectos/p-1/cultivos').flush([]);
    http.expectOne('http://localhost:8000/proyectos/p-1/cultivos/balance').flush(BALANCE);
    http.expectOne('http://localhost:8000/catalogos/cultivos').flush([]);
    http
      .expectOne('http://localhost:8000/proyectos/p-1')
      .error(new ProgressEvent('error'), { status: 0 });

    expect(store.estado()).toBe('error');
    expect(store.error()).toContain('No pudimos conectar con el servidor');
  });
});
