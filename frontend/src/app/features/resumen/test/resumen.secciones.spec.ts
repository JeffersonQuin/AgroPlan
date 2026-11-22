import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { ResumenPage } from '../resumen.page';

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

function terreno(pendiente: number | null) {
  return {
    nombre_parcela: 'La Hoyada',
    area_m2: 3200,
    caudal_disponible_m3h: 1.8,
    caudal_efectivo_m3h: 1.8,
    suelo_codigo: 'franco_arenado',
    fuente_agua: 'pozo',
    pendiente_pct: pendiente,
    geometria: {
      vertices: [
        { x: 0, y: 0 },
        { x: 40, y: 0 },
        { x: 40, y: 80 },
        { x: 0, y: 80 },
      ],
    },
  };
}

const BLOQUES = [
  {
    id: 'b-1',
    cultivo_codigo: 'papa',
    color: '#8D6E63',
    poligono: { anillo: [[0, 0], [40, 0], [40, 56], [0, 56]] },
    area_m2: 2240,
    centroide: { x: 20, y: 28 },
    nombre: 'Papa',
    porcentaje: 70,
    demanda_pico_l_dia: 4480,
    siembra: '2026-03-15',
    cosecha: '2026-07-15',
    ciclo_dias: 122,
    kc: 1.15,
    imagen_url: 'https://commons.example/papa.jpg',
    imagen_credito: 'Wikimedia Commons · CC BY-SA 4.0',
  },
  {
    id: 'b-2',
    cultivo_codigo: 'lechuga',
    color: '#4CAF50',
    poligono: { anillo: [[40, 0], [60, 0], [60, 24], [40, 56]] },
    area_m2: 960,
    centroide: { x: 50, y: 20 },
    nombre: 'Lechuga',
    porcentaje: 30,
    demanda_pico_l_dia: 1920,
    siembra: '2026-03-20',
    cosecha: '2026-05-25',
    ciclo_dias: 66,
    kc: 1,
    imagen_url: null,
    imagen_credito: null,
  },
];

const SISTEMA = {
  id: 's-1',
  tipo: 'goteo',
  fuente_agua: 'pozo',
  tanque_l: 5000,
  bomba_hp: 1,
  diametro_principal_mm: 32,
  emisor: { tipo: 'gotero', caudal_lh: 2, separacion_m: 0.3 },
  separacion_laterales_m: 0.8,
  orientacion: 'E-O',
  punto_conexion: { x: 0, y: 0 },
  num_sectores: 2,
  red_generada_en: '2026-11-21T12:00:00',
  parametros_version: 1,
};

const SECTORES = [
  {
    id: 'sec-1',
    numero: 1,
    etiqueta: 'Papa',
    poligono: { anillo: [[0, 0], [40, 0], [40, 56], [0, 56]] },
    area_m2: 2240,
    num_goteros: 1120,
    caudal_m3h: 2.24,
    secuencia: 1,
    cultivo_ids: ['b-1'],
  },
  {
    id: 'sec-2',
    numero: 2,
    etiqueta: 'Lechuga',
    poligono: { anillo: [[40, 0], [60, 0], [60, 24], [40, 56]] },
    area_m2: 960,
    num_goteros: 480,
    caudal_m3h: 0.96,
    secuencia: 2,
    cultivo_ids: ['b-2'],
  },
];

const RED = {
  nodos: [
    { id: 'n-1', tipo: 'tanque', geometria: { x: -6, y: 80 }, tramo_id: null, atributos: {} },
    { id: 'n-2', tipo: 'bomba', geometria: { x: -6, y: 70 }, tramo_id: 't-1', atributos: {} },
    { id: 'n-3', tipo: 'valvula', geometria: { x: 0, y: 0 }, tramo_id: 't-1', atributos: {} },
  ],
  tramos: [
    {
      id: 't-1',
      sector_id: null,
      tipo: 'principal',
      diametro_mm: 32,
      longitud_m: 78,
      caudal_m3h: 1.8,
      orden: 1,
      puntos: [[-6, 80], [-6, 0], [0, 0]],
    },
    {
      id: 't-2',
      sector_id: 'sec-1',
      tipo: 'lateral',
      diametro_mm: 16,
      longitud_m: 420,
      caudal_m3h: 1.8,
      orden: 2,
      puntos: [[0, 0], [40, 0]],
    },
  ],
  emisores: [
    {
      tramo_id: 't-2',
      separacion_m: 0.3,
      puntos: [[0, 0], [2, 0], [4, 0]] as [number, number][],
    },
  ],
};

const CALENDARIO = [
  {
    bloque_id: 'b-1',
    cultivo_codigo: 'papa',
    etiqueta: 'Papa',
    siembra: '2026-03-15',
    cosecha: '2026-07-15',
  },
  {
    bloque_id: 'b-2',
    cultivo_codigo: 'lechuga',
    etiqueta: 'Lechuga',
    siembra: '2026-03-20',
    cosecha: '2026-05-25',
  },
];

const MATERIALES = [
  {
    rubro: 'Tubería',
    descripcion: 'Tubería PVC Ø32 mm',
    cantidad: 78,
    unidad: 'm',
    moneda: 'BOB',
    precio_unitario_bs: 15,
    total_bs: 1170,
    fuente_url: 'https://ferreteria.example/pvc',
    recuperado_en: '2026-02-12T10:00:00',
    reutilizado: true,
  },
  {
    rubro: 'Goteros',
    descripcion: 'Goteros autocompensantes 2.0 L/h',
    cantidad: 1600,
    unidad: 'u',
    moneda: 'BOB',
    precio_unitario_bs: null,
    total_bs: null,
    fuente_url: null,
    recuperado_en: null,
    reutilizado: false,
  },
];

function resultadoCompleto() {
  return {
    proyecto_id: 'p-1',
    nombre: 'Los Olivos',
    estado: 'completado',
    diseno: {
      bloques: BLOQUES,
      sistema: SISTEMA,
      sectores: SECTORES,
      red: RED,
      computo: { tuberia_m: 498, goteros_u: 1600, valvulas_u: 2 },
      advertencias: [
        {
          codigo: 'demanda_alta',
          mensaje: 'La demanda pico supera la autonomía del tanque.',
          bloqueante: false,
          campo: null,
        },
      ],
      cifras: {
        presion_trabajo_bar: 1.5,
        caudal_sector_m3h: 1.8,
        tiempo_riego_h: 3.2,
        autonomia_dias: 0.8,
        demanda_pico_l_dia: 6400,
      },
      cifras_agente: {
        presion_trabajo_bar: 1.3,
        eficiencia_pct: 92,
        demanda_pico_l_dia: 6400,
        autonomia_dias: 1,
        tiempo_riego_h: 3,
        turnos: [
          { sector: 1, horas: 3.2, caudal_lh: 1800 },
          { sector: 2, horas: 3.2, caudal_lh: 1800 },
        ],
      },
      eficiencia_pct: 92,
      calendario: CALENDARIO,
      materiales: MATERIALES,
      presupuesto_bs: 2000,
      costo_total_bs: 1170,
      presupuesto_excedido: false,
      recomendaciones: [
        {
          id: 'r-1',
          tipo: 'final',
          titulo: 'Operar turnos secuenciales e independientes',
          detalle: 'No superar el aforo de 1.8 m³/h y mantener 1.5 bar.',
          justificacion: 'La fuente entrega 1.8 m³/h y cada sector lo consume completo.',
          aplicada: null,
        },
      ],
      fuentes: [
        {
          id: 'f-1',
          tipo: 'web',
          titulo: 'Ficha técnica del gotero',
          url: 'https://example.com/gotero',
          fragmento: 'Caudal 2 L/h a 1.5 bar.',
          recuperado_en: '2026-02-12T10:00:00',
        },
      ],
      ajustes: [
        {
          campo: 'presion_trabajo_bar',
          valor_agente: '1.30 bar',
          valor_motor: '1.50 bar',
          motivo: 'La red pierde 0.2 bar en el tramo principal.',
        },
      ],
    },
    advertencias: [
      {
        codigo: 'presion_ajustada',
        mensaje: 'El motor ajustó la presión de trabajo a 1.5 bar.',
        bloqueante: false,
        campo: 'presion_trabajo_bar',
      },
    ],
  };
}

function resultadoMinimo() {
  return {
    proyecto_id: 'p-1',
    nombre: 'Los Olivos',
    estado: 'completado',
    diseno: {
      bloques: [
        {
          ...BLOQUES[0],
          id: 'b-min',
          porcentaje: null,
          demanda_pico_l_dia: null,
          siembra: null,
          cosecha: null,
          ciclo_dias: null,
          kc: null,
          imagen_url: null,
          imagen_credito: null,
        },
      ],
      sistema: SISTEMA,
      sectores: [],
      red: { nodos: [], tramos: [], emisores: [] },
      computo: { tuberia_m: 0, goteros_u: 0, valvulas_u: 0 },
      advertencias: [],
      cifras: {
        presion_trabajo_bar: null,
        caudal_sector_m3h: null,
        tiempo_riego_h: null,
        autonomia_dias: null,
        demanda_pico_l_dia: null,
      },
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
    advertencias: [],
  };
}

describe('ResumenPage (paso 4: secciones del informe)', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'proyectos/:proyectoId/resultado', component: ResumenPage },
          { path: 'proyectos/:proyectoId/cultivos', component: ResumenPage },
          { path: 'proyectos/:proyectoId/riego', component: ResumenPage },
          { path: 'proyectos/:proyectoId/terreno', component: ResumenPage },
        ]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  beforeEach(() => {
    localStorage.setItem(
      CLAVE_BORRADOR,
      JSON.stringify({
        proyectoId: 'p-1',
        productos: [{ codigo: 'papa', texto: 'papa', etiqueta: 'Papa', color: '#8D6E63' }],
        siembra: '2026-11-21',
        restricciones: { energia: 'solar', tanque_l: 5000, presupuesto_bs: 2000 },
      }),
    );
  });

  async function montar(resultado: Record<string, unknown>, pendiente: number | null = 1.5) {
    const harness = await RouterTestingHarness.create('/proyectos/p-1/resultado');
    http.expectOne(`${BASE}/p-1`).flush(PROYECTO);
    http.expectOne(`${BASE}/p-1/terreno`).flush(terreno(pendiente));
    http.expectOne(`${API}/catalogos/suelos`).flush(SUELOS);
    http.expectOne(`${API}/catalogos/cultivos`).flush(CATALOGO);
    http.expectOne(`${BASE}/p-1/resultado`).flush(resultado);
    await harness.fixture.whenStable();
    return harness.routeNativeElement as HTMLElement;
  }

  function html(selector: string, raiz: HTMLElement): HTMLElement {
    const encontrado = raiz.querySelector(selector) as HTMLElement | null;
    if (encontrado === null) throw new Error(`No se encontró ${selector}`);
    return encontrado;
  }

  it('muestra todas las secciones con un resultado completo', async () => {
    const pagina = await montar(resultadoCompleto());
    const secciones = html('[data-secciones-informe]', pagina);

    // 1. Datos del terreno, con hectáreas, pendiente y el link al paso 1.
    const terrenoCard = html('[data-seccion-terreno]', pagina);
    for (const texto of ['La Hoyada', '3200 m²', '0.32 ha', 'Franco arenado', 'Pozo']) {
      expect(terrenoCard.textContent).toContain(texto);
    }
    expect(terrenoCard.textContent).toContain('1.8 m³/h');
    expect(terrenoCard.textContent).toContain('1.5 %');
    const linkTerreno = terrenoCard.querySelector('a') as HTMLAnchorElement;
    expect(linkTerreno.getAttribute('href')).toBe('/proyectos/p-1/terreno');

    // 2. Zonificación con imagen, crédito, badge, área, ciclo, demanda y fechas.
    const bloquePapa = html('[data-bloque]', secciones);
    expect(bloquePapa.querySelector('img')?.getAttribute('src')).toBe(
      'https://commons.example/papa.jpg',
    );
    expect(bloquePapa.textContent).toContain('Wikimedia Commons');
    for (const texto of ['70%', '2240 m²', 'Ciclo: 122 d', '4480 L/día', '15 mar 2026', '15 jul 2026']) {
      expect(bloquePapa.textContent).toContain(texto);
    }
    const bloques = secciones.querySelectorAll('[data-bloque]');
    expect(bloques.length).toBe(2);
    // Sin imagen: placeholder con la inicial del bloque.
    expect(bloques[1].querySelector('img')).toBeNull();
    expect(bloques[1].textContent).toContain('L');

    // 3. Tecnología y cabezal.
    const tecnologia = html('[data-seccion-tecnologia]', secciones);
    for (const texto of ['Goteo localizado', '5000 L', '1 HP', '2 L/h', '0.3 m', '92%']) {
      expect(tecnologia.textContent).toContain(texto);
    }

    // 4. Plano 2D desde la red real, con leyenda de los diámetros de los tramos.
    const plano = html('[data-plano-red]', secciones);
    const svg = plano.querySelector('[data-plano-svg]') as SVGSVGElement;
    expect(svg).not.toBeNull();
    const trazos = svg.querySelectorAll('polyline');
    expect(trazos.length).toBe(2);
    expect(trazos[0].getAttribute('points')).toContain('0');
    expect(svg.querySelectorAll('circle').length).toBeGreaterThanOrEqual(3);
    const leyenda = html('[data-leyenda-plano]', plano);
    expect(leyenda.textContent).toContain('PVC Ø32 mm');
    expect(leyenda.textContent).toContain('PE Ø16 mm');

    // 5. Balance con cifras del motor, del agente y el ajuste explicado.
    const balance = html('[data-seccion-balance]', secciones);
    expect(balance.textContent).toContain('1.5 bar');
    expect(balance.textContent).toContain('6400 L/día');
    const cifrasAgente = html('[data-cifras-agente]', balance);
    expect(cifrasAgente.textContent).toContain('1.3 bar');
    expect(cifrasAgente.textContent).toContain('S1');
    const ajuste = html('[data-ajuste]', balance);
    expect(ajuste.textContent).toContain('de 1.30 bar a 1.50 bar');
    expect(ajuste.textContent).toContain('La red pierde 0.2 bar en el tramo principal.');

    // 6. Cómputo con precios, reutilización y comparación con el presupuesto.
    const computo = html('[data-seccion-computo]', secciones);
    const filas = computo.querySelectorAll('[data-material]');
    expect(filas.length).toBe(2);
    expect(filas[0].textContent).toContain('Tubería PVC Ø32 mm');
    expect(filas[0].textContent).toContain('78');
    expect(filas[0].textContent).toContain('1170 Bs');
    expect(filas[0].textContent).toContain('precio reutilizado');
    expect(filas[0].textContent).toContain('12 feb 2026');
    expect(filas[1].textContent).toContain('sin precio informado');
    expect(html('[data-costo-total]', computo).textContent).toContain('1170 Bs');
    expect(html('[data-costo-total]', computo).textContent).toContain('2000 Bs');
    expect(html('[data-presupuesto-estado]', computo).textContent).toContain(
      'Dentro del presupuesto',
    );

    // 7. Calendario, recomendaciones con justificación y fuentes.
    const calendario = html('[data-seccion-calendario]', secciones);
    expect(calendario.textContent).toContain('Papa');
    expect(calendario.textContent).toContain('15 mar 2026');
    expect(calendario.textContent).toContain('15 jul 2026');
    const recomendaciones = html('[data-seccion-recomendaciones]', secciones);
    expect(recomendaciones.textContent).toContain('Operar turnos secuenciales e independientes');
    expect(recomendaciones.textContent).toContain(
      'La fuente entrega 1.8 m³/h y cada sector lo consume completo.',
    );
    const fuentes = html('[data-seccion-fuentes]', secciones);
    expect(fuentes.textContent).toContain('Ficha técnica del gotero');
    expect(fuentes.querySelector('a')?.getAttribute('href')).toBe(
      'https://example.com/gotero',
    );

    // 8. Advertencias arriba de todo, no al pie.
    const advertencias = html('[data-advertencias]', pagina);
    expect(advertencias.textContent).toContain(
      'El motor ajustó la presión de trabajo a 1.5 bar.',
    );
    expect(advertencias.textContent).toContain(
      'La demanda pico supera la autonomía del tanque.',
    );
    const posicion = advertencias.compareDocumentPosition(secciones);
    expect(posicion & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('muestra "no informado" con un resultado mínimo y no rompe', async () => {
    const pagina = await montar(resultadoMinimo(), null);
    const secciones = html('[data-secciones-informe]', pagina);

    // Imagen ausente: placeholder con la inicial del bloque.
    const bloque = html('[data-bloque]', secciones);
    expect(bloque.querySelector('img')).toBeNull();
    expect(bloque.textContent).toContain('P');
    expect(bloque.textContent).toContain('no informado');

    // Sin red: mensaje en vez de un plano inventado.
    expect(secciones.querySelector('[data-plano-svg]')).toBeNull();
    expect(html('[data-plano-vacio]', secciones)).not.toBeNull();

    // Sin precios ni cifras del agente: "no informado", nunca cero.
    expect(html('[data-seccion-balance]', secciones).textContent).toContain('no informado');
    expect(secciones.querySelector('[data-cifras-agente]')).toBeNull();
    expect(secciones.querySelector('[data-ajuste]')).toBeNull();
    expect(html('[data-seccion-computo]', secciones).textContent).toContain('no informado');
    expect(html('[data-seccion-calendario]', secciones).textContent).toContain('no informado');
    expect(html('[data-seccion-recomendaciones]', secciones).textContent).toContain(
      'no informado',
    );
    expect(html('[data-seccion-fuentes]', secciones).textContent).toContain('no informado');
    expect(pagina.querySelector('[data-error-informe]')).toBeNull();
  });
});
