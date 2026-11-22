import { TestBed } from '@angular/core/testing';
import { WATER_SOURCE_OPTIONS } from '../models/terrain.model';
import { TerrainStore } from '../state/terrain.store';

describe('TerrainStore', () => {
  let store: TerrainStore;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    store = TestBed.inject(TerrainStore);
  });

  it('starts from the cotas of the mockup, measured for real', () => {
    expect(store.name()).toBe('Mi parcela');
    expect(store.shape()).toBe('trapecio');
    // Las cotas del diseño dan 2.100 m², no los 3.200 que mostraba el mockup.
    expect(store.areaHaLabel()).toBe('0.21 ha');
    expect(store.areaSqMLabel()).toBe('(2,100 m²)');
    expect(store.perimeterLabel()).toBe('186.1 m');
    expect(store.verticesLabel()).toBe('4 lados (trapecio)');
    expect(store.diagonalLabel()).toBe('36.06 m');
    expect(store.desnivelLabel()).toBe('0.60 m (1% pend.) · pendiente asumida');
    expect(store.slopeLabel()).toBe('1.0 %');
    expect(store.infiltrationLabel()).toBe('Infiltración: 15-25 mm/h');
  });

  it('draws the same figure it sends to the backend', () => {
    expect(store.vertices().length).toBe(5);

    store.setShape('rectangulo');

    expect(store.vertices().length).toBe(4);
    expect(store.aPayload().vertices.length).toBe(4);
    expect(store.aPayload().forma).toBe('rectangulo');
    expect(store.metrics().areaM2).toBe(2400);
    expect(store.cotasVisibles().bottomM).toBe(false);
    expect(store.cotasVisibles().rightM).toBe(false);
  });

  it('replaces the reference metrics with real geometry when a cota changes', () => {
    store.setDimension('topM', 50);

    expect(store.metrics().areaM2).toBe(1800);
    expect(store.areaHaLabel()).toBe('0.18 ha');
  });

  it('derives the vertical drop from the slope', () => {
    store.setSlope(2.5);

    expect(store.desnivelLabel()).toBe('1.50 m (2.5% pend.)');
    expect(store.slopeLabel()).toBe('2.5 %');
  });

  it('assumes the slope until the user says they know it', () => {
    expect(store.pendienteAsumida()).toBe(true);
    expect(store.slopePct()).toBe(1);
    expect(store.aPayload().pendiente_pct).toBe(1);
    expect(store.desnivelLabel()).toContain('pendiente asumida');

    store.setSlope(4.5);

    expect(store.pendienteAsumida()).toBe(false);
    expect(store.aPayload().pendiente_pct).toBe(4.5);
    expect(store.desnivelLabel()).not.toContain('asumida');

    store.usarPendienteAsumida();
    expect(store.pendienteAsumida()).toBe(true);
    expect(store.slopePct()).toBe(1);
  });

  it('offers the five water sources the backend knows', () => {
    expect(WATER_SOURCE_OPTIONS.map((opcion) => opcion.value)).toEqual([
      'pozo',
      'tanque',
      'red',
      'cisterna',
      'pila',
    ]);

    store.setWaterSource('pila');
    expect(store.aPayload().fuente_agua).toBe('pila');
  });

  it('follows the shape, soil and water source selections', () => {
    store.setShape('rectangulo');
    store.setSoil('arenoso');
    store.setWaterSource('cisterna');

    expect(store.verticesLabel()).toBe('4 lados (rectángulo)');
    expect(store.infiltrationLabel()).toBe('Infiltración: > 30 mm/h');
    expect(store.waterSource()).toBe('cisterna');
  });

  it('keeps the parcel identity and the water figures', () => {
    store.setName('Parcela Sur');
    store.setFlow(2.4);
    store.setStaticLevel(22);

    expect(store.name()).toBe('Parcela Sur');
    expect(store.flowM3h()).toBe(2.4);
    expect(store.staticLevelM()).toBe(22);
  });
});

/* -------------------------------------------------------------------------- */
/* Backend: carga y guardado                                                   */
/* -------------------------------------------------------------------------- */

import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

const PROYECTO = {
  id: 'p-1',
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

const TERRENO = {
  id: 't-1',
  nombre_parcela: 'Parcela Norte',
  forma: 'trapecio',
  geometria: {
    vertices: [
      { x: 0, y: 40 },
      { x: 60, y: 40 },
      { x: 60, y: 20 },
      { x: 30, y: 0 },
      { x: 0, y: 0 },
    ],
    cerrado: true,
    unidad: 'm',
    eje_y: 'norte',
  },
  area_m2: 1800,
  perimetro_m: 172.4,
  lados: 5,
  lados_m: [],
  suelo_codigo: 'franco',
  pendiente_pct: 2,
  fuente_agua: 'pozo',
  caudal_disponible_m3h: 2.5,
  caudal_efectivo_m3h: 2.5,
  caudal_origen: 'cliente',
  caudal_sugerido_m3h: null,
  profundidad_nivel_dinamico_m: 18,
  alertas: [],
};

describe('TerrainStore contra el backend', () => {
  let store: TerrainStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(TerrainStore);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function cargar(terreno: typeof TERRENO | null): void {
    store.cargar('p-1');
    http.expectOne('http://localhost:8000/proyectos/p-1').flush(PROYECTO);
    const peticionTerreno = http.expectOne('http://localhost:8000/proyectos/p-1/terreno');
    if (terreno === null) {
      peticionTerreno.flush({ detail: 'El proyecto todavía no tiene terreno' }, { status: 404, statusText: 'Not Found' });
    } else {
      peticionTerreno.flush(terreno);
    }
    http
      .expectOne('http://localhost:8000/catalogos/suelos')
      .flush([
        { codigo: 'franco', nombre: 'Franco', infiltracion_mm_h: 12, retencion_agua_mm_m: 160 },
      ]);
  }

  it('loads the project name and the soil catalogue on a fresh project', () => {
    cargar(null);

    expect(store.nombreProyecto()).toBe('Los Olivos');
    expect(store.estado()).toBe('inicial');
    expect(store.derivado()).toBeNull();
    expect(store.infiltrationLabel()).toBe('Infiltración: 12 mm/h');
    expect(store.guardadoLabel()).toBe('Sin guardar');
  });

  it('offers the soils the backend actually has', () => {
    cargar(null);

    expect(store.opcionesSuelo()).toEqual([
      { value: 'franco', label: 'Franco · 12 mm/h', infiltration: '12 mm/h' },
    ]);
  });

  it('saves with PUT the first time and with PATCH afterwards', () => {
    cargar(null);

    store.guardar();
    const primera = http.expectOne('http://localhost:8000/proyectos/p-1/terreno');
    expect(primera.request.method).toBe('PUT');
    expect(primera.request.body.forma).toBe('trapecio');
    expect(primera.request.body.vertices.length).toBe(5);
    expect(primera.request.body.suelo_codigo).toBe('franco');
    // Sin informar: el backend asigna el caudal y el nivel queda vacío.
    expect(primera.request.body.caudal_disponible_m3h).toBeNull();
    expect(primera.request.body.profundidad_nivel_dinamico_m).toBeNull();
    primera.flush(TERRENO);

    expect(store.estado()).toBe('guardado');
    expect(store.derivado()?.areaM2).toBe(1800);
    expect(store.verticesLabel()).toBe('5 lados');
    expect(store.caudalOrigenLabel()).toBe('Informado por vos');

    store.guardar();
    const segunda = http.expectOne('http://localhost:8000/proyectos/p-1/terreno');
    expect(segunda.request.method).toBe('PATCH');
    segunda.flush(TERRENO);
  });

  it('shows the backend numbers over the local preview once saved', () => {
    cargar(TERRENO);

    expect(store.estado()).toBe('guardado');
    expect(store.areaHaLabel()).toBe('0.18 ha');
    expect(store.areaSqMLabel()).toBe('(1,800 m²)');
    expect(store.perimeterLabel()).toBe('172.4 m');
    // Las cotas se reconstruyen desde el polígono guardado.
    expect(store.dimensions().topM).toBe(60);
    expect(store.dimensions().leftM).toBe(40);
    expect(store.caudalLabel()).toBe('2.5 m³/h');
  });

  it('takes the project name when the parcel has none yet', () => {
    cargar(null);

    expect(store.name()).toBe('Los Olivos');

    store.setName('La Cañada');
    expect(store.name()).toBe('La Cañada');
  });

  it('keeps the informed flow and level when the user types them', () => {
    cargar(null);
    store.setFlow(2.4);
    store.setStaticLevel(21);

    store.guardar();
    const peticion = http.expectOne('http://localhost:8000/proyectos/p-1/terreno');
    expect(peticion.request.body.caudal_disponible_m3h).toBe(2.4);
    expect(peticion.request.body.profundidad_nivel_dinamico_m).toBe(21);
    peticion.flush(TERRENO);
  });

  it('flags a polygon that crosses itself and a tiny area', () => {
    cargar(null);

    expect(store.validaciones().every((validacion) => validacion.ok)).toBe(true);
    expect(store.validaciones().map((validacion) => validacion.ok).length).toBe(4);

    store.setDimension('topM', 5);
    store.setDimension('bottomM', 2);
    store.setDimension('leftM', 3);

    const falla = store.validaciones().find((validacion) => !validacion.ok);
    expect(falla?.texto).toContain('Superficie insuficiente');
  });

  it('sends zero flow and level as "not informed"', () => {
    cargar(null);
    store.setFlow(0);
    store.setStaticLevel(0);

    expect(store.flowM3h()).toBeNull();
    expect(store.staticLevelM()).toBeNull();

    store.guardar();
    const peticion = http.expectOne('http://localhost:8000/proyectos/p-1/terreno');
    expect(peticion.request.body.caudal_disponible_m3h).toBeNull();
    expect(peticion.request.body.profundidad_nivel_dinamico_m).toBeNull();
    peticion.flush(TERRENO);
  });

  it('retries as PATCH when the terrain already existed', () => {
    cargar(null);

    store.guardar();
    http
      .expectOne('http://localhost:8000/proyectos/p-1/terreno')
      .flush({ detail: 'El proyecto ya tiene terreno; usa PATCH' }, { status: 409, statusText: 'Conflict' });

    const reintento = http.expectOne('http://localhost:8000/proyectos/p-1/terreno');
    expect(reintento.request.method).toBe('PATCH');
    reintento.flush(TERRENO);

    expect(store.estado()).toBe('guardado');
  });

  it('reports the save error without losing the form', () => {
    cargar(null);
    store.setName('Parcela Sur');

    store.guardar();
    http
      .expectOne('http://localhost:8000/proyectos/p-1/terreno')
      .flush({ detail: 'El suelo ya no existe' }, { status: 422, statusText: 'Unprocessable' });

    expect(store.estado()).toBe('error');
    expect(store.error()).toBe('El suelo ya no existe');
    expect(store.name()).toBe('Parcela Sur');
  });
});
