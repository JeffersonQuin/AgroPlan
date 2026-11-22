import { TestBed } from '@angular/core/testing';
import { PlanoRed } from '../components/plano-red/plano-red';
import {
  BloqueInformeApi,
  RedInformeApi,
  SectorInformeApi,
  SistemaInformeApi,
  TerrenoResumen,
} from '../models/resumen.model';

/** Trapecio real del caso del usuario: 2100 m², cinco vértices (L3). */
const TERRENO: TerrenoResumen = {
  nombre: 'La Hoyada',
  areaM2: 2100,
  sueloCodigo: 'franco_arenado',
  sueloNombre: 'Franco arenado',
  fuenteLabel: 'Pozo',
  caudalM3h: 1.8,
  pendientePct: 1.5,
  geometria: {
    vertices: [
      { x: 0, y: 40 },
      { x: 60, y: 40 },
      { x: 60, y: 20 },
      { x: 30, y: 0 },
      { x: 0, y: 0 },
    ],
  },
};

const BLOQUES: BloqueInformeApi[] = [
  {
    id: 'b-1',
    cultivo_codigo: 'papa',
    color: '#8D6E63',
    poligono: { anillo: [[0, 0], [30, 0], [30, 40], [0, 40]] as [number, number][] },
    area_m2: 1200,
    centroide: { x: 15, y: 20 },
    nombre: 'Papa',
    porcentaje: 57,
    demanda_pico_l_dia: 2400,
    siembra: '2026-03-15',
    cosecha: '2026-07-15',
    ciclo_dias: 122,
    kc: 1.15,
    imagen_url: null,
    imagen_credito: null,
  },
  {
    id: 'b-2',
    cultivo_codigo: 'lechuga',
    color: '#4CAF50',
    poligono: { anillo: [[30, 0], [60, 20], [60, 40], [30, 40]] as [number, number][] },
    area_m2: 900,
    centroide: { x: 45, y: 25 },
    nombre: 'Lechuga',
    porcentaje: 43,
    demanda_pico_l_dia: 1800,
    siembra: '2026-03-20',
    cosecha: '2026-05-25',
    ciclo_dias: 66,
    kc: 1,
    imagen_url: null,
    imagen_credito: null,
  },
];

const SECTORES: SectorInformeApi[] = [
  {
    id: 'sec-1',
    numero: 1,
    etiqueta: 'Sector 1',
    poligono: { anillo: [[0, 0], [30, 0], [30, 40], [0, 40]] },
    area_m2: 1200,
    num_goteros: 600,
    caudal_m3h: 1.2,
    secuencia: 1,
    cultivo_ids: ['b-1'],
  },
  {
    id: 'sec-2',
    numero: 2,
    etiqueta: 'Sector 2',
    poligono: { anillo: [[30, 0], [60, 20], [60, 40], [30, 40]] },
    area_m2: 900,
    num_goteros: 450,
    caudal_m3h: 0.9,
    secuencia: 2,
    cultivo_ids: ['b-2'],
  },
];

const SISTEMA: SistemaInformeApi = {
  id: 's-1',
  tipo: 'goteo',
  fuente_agua: 'pozo',
  tanque_l: 5000,
  bomba_hp: 1,
  diametro_principal_mm: 32,
  emisor: { tipo: 'gotero', caudal_lh: 2, separacion_m: 0.3 },
  separacion_laterales_m: 0.8,
  orientacion: 'E-O',
  punto_conexion: { x: 0, y: 40 },
  num_sectores: 2,
  red_generada_en: '2026-11-21T12:00:00',
  parametros_version: 1,
};

const RED: RedInformeApi = {
  nodos: [
    { id: 'n-1', tipo: 'tanque', geometria: { x: -5, y: 40 }, tramo_id: null, atributos: {} },
    { id: 'n-2', tipo: 'bomba', geometria: { x: -5, y: 34 }, tramo_id: 't-1', atributos: {} },
    { id: 'n-3', tipo: 'valvula', geometria: { x: 0, y: 40 }, tramo_id: 't-1', atributos: {} },
  ],
  tramos: [
    {
      id: 't-1',
      sector_id: null,
      tipo: 'principal',
      diametro_mm: 32,
      longitud_m: 40,
      caudal_m3h: 1.8,
      orden: 1,
      puntos: [[-5, 40], [0, 40], [0, 0]],
    },
    {
      id: 't-2',
      sector_id: 'sec-1',
      tipo: 'lateral',
      diametro_mm: 12,
      longitud_m: 20,
      caudal_m3h: 1.2,
      orden: 2,
      puntos: [[0, 0], [30, 0]],
    },
    {
      id: 't-3',
      sector_id: 'sec-2',
      tipo: 'lateral',
      diametro_mm: 16,
      longitud_m: 20,
      caudal_m3h: 0.9,
      orden: 3,
      puntos: [[30, 0], [60, 20]],
    },
    {
      id: 't-4',
      sector_id: 'sec-2',
      tipo: 'lateral',
      diametro_mm: 20,
      longitud_m: 10,
      caudal_m3h: 0.9,
      orden: 4,
      puntos: [[45, 25], [55, 35]],
    },
  ],
  emisores: [
    { tramo_id: 't-2', separacion_m: 0.3, puntos: [[0, 0], [2, 0], [4, 0]] },
    { tramo_id: 't-3', separacion_m: 0.3, puntos: [[30, 0], [32, 1]] },
    { tramo_id: 't-4', separacion_m: 0.3, puntos: [[45, 25]] },
  ],
};

/** Red con muchos goteros: el caso del usuario (14.000 emisores). */
function redDensa(total: number): RedInformeApi {
  const puntos: [number, number][] = [];
  for (let indice = 0; indice < total; indice++) {
    puntos.push([(indice % 60) + 0.5, Math.floor(indice / 60) * 0.4 + 0.2]);
  }
  return {
    nodos: RED.nodos,
    tramos: RED.tramos,
    emisores: [{ tramo_id: 't-2', separacion_m: 0.3, puntos }],
  };
}

function puntosDe(elemento: Element): number {
  return (elemento.getAttribute('points') ?? '').trim().split(/\s+/).filter(Boolean).length;
}

/** Red con muchos laterales: el caso del usuario (una parrilla de goteo densa). */
function redConLaterales(total: number): RedInformeApi {
  const tramos: RedInformeApi['tramos'] = [
    {
      id: 't-1',
      sector_id: null,
      tipo: 'principal',
      diametro_mm: 32,
      longitud_m: 40,
      caudal_m3h: 1.8,
      orden: 1,
      puntos: [[-5, 40], [0, 40], [0, 0]],
    },
  ];
  for (let indice = 0; indice < total; indice++) {
    const y = (indice % 40) + 0.5;
    tramos.push({
      id: `t-lat-${indice}`,
      sector_id: 'sec-1',
      tipo: 'lateral',
      diametro_mm: 12,
      longitud_m: 30,
      caudal_m3h: 1.2,
      orden: indice + 2,
      puntos: [[0, y], [30, y]],
    });
  }
  return { nodos: RED.nodos, tramos, emisores: [] };
}

describe('PlanoRed (plano del informe)', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PlanoRed],
    }).compileComponents();
  });

  function montarConFixture(red: RedInformeApi) {
    const fixture = TestBed.createComponent(PlanoRed);
    fixture.componentRef.setInput('red', red);
    fixture.componentRef.setInput('bloques', BLOQUES);
    fixture.componentRef.setInput('sectores', SECTORES);
    fixture.componentRef.setInput('sistema', SISTEMA);
    fixture.componentRef.setInput('terreno', TERRENO);
    fixture.detectChanges();
    return { fixture, plano: fixture.nativeElement as HTMLElement };
  }

  function montar(red: RedInformeApi): HTMLElement {
    return montarConFixture(red).plano;
  }

  it('dibuja terreno, zonas de cultivo y sectores debajo de la red (S4)', () => {
    const plano = montar(RED);
    const svg = plano.querySelector('[data-plano-svg]') as SVGSVGElement;
    expect(svg).not.toBeNull();

    // 1. El contorno del terreno es el polígono real del trapecio, con sus cinco vértices.
    const terreno = svg.querySelector('[data-plano-terreno]') as SVGPolygonElement;
    expect(terreno).not.toBeNull();
    expect(terreno.tagName.toLowerCase()).toBe('polygon');
    expect(puntosDe(terreno)).toBe(5);

    // 2. Un relleno por bloque, con el color del bloque y su nombre + porcentaje.
    const zonas = Array.from(svg.querySelectorAll<SVGPolygonElement>('[data-zona]'));
    expect(zonas.map((zona) => zona.getAttribute('fill'))).toEqual(['#8D6E63', '#4CAF50']);

    const etiquetasZona = Array.from(
      svg.querySelectorAll<SVGTextElement>('[data-zona-etiqueta]'),
    ).map((texto) => texto.textContent?.trim() ?? '');
    expect(etiquetasZona.length).toBe(2);
    expect(etiquetasZona[0]).toContain('Papa');
    expect(etiquetasZona[0]).toContain('57');
    expect(etiquetasZona[1]).toContain('Lechuga');
    expect(etiquetasZona[1]).toContain('43');

    // 3. Los sectores tienen contorno propio (línea punteada) y su etiqueta.
    const sectores = Array.from(svg.querySelectorAll<SVGPolygonElement>('[data-sector]'));
    expect(sectores.length).toBe(2);
    for (const sector of sectores) {
      expect(sector.getAttribute('stroke-dasharray')).toBeTruthy();
    }
    const etiquetasSector = Array.from(
      svg.querySelectorAll<SVGTextElement>('[data-sector-etiqueta]'),
    ).map((texto) => texto.textContent?.trim() ?? '');
    expect(etiquetasSector).toEqual(['Sector 1', 'Sector 2']);

    // 4. La red sigue arriba: un trazo por tramo. Los emisores son ruido y no se
    //    dibujan por defecto: se encienden desde su control (S4).
    expect(svg.querySelectorAll('polyline').length).toBe(RED.tramos.length);
    expect(svg.querySelectorAll('[data-emisor]').length).toBe(0);
    expect(plano.querySelector('[data-toggle-emisores]')).not.toBeNull();

    // 5. Orden de lectura: terreno → zonas → sectores → red → emisores → nodos, y las
    //    etiquetas al final para que la red nunca las tape.
    const capas = Array.from(svg.querySelectorAll('[data-capa]')).map((capa) =>
      capa.getAttribute('data-capa'),
    );
    expect(capas).toEqual([
      'terreno',
      'zonas',
      'sectores',
      'red',
      'emisores',
      'nodos',
      'etiquetas',
    ]);
  });

  it('la leyenda distingue cada capa y agrupa los diámetros (S4)', () => {
    const plano = montar(RED);
    const leyenda = plano.querySelector('[data-leyenda-plano]') as HTMLElement;
    const texto = leyenda.textContent ?? '';

    for (const etiqueta of [
      'Borde del terreno',
      'Zona de cultivo',
      'Sector de riego',
      'Matriz',
      'Lateral',
      'Emisor',
      'Válvula',
    ]) {
      expect(texto).toContain(etiqueta);
    }
    // Un solo renglón para los laterales, con sus tres diámetros agrupados.
    const renglonesLateral = Array.from(leyenda.querySelectorAll('[data-leyenda-tramo]')).filter(
      (renglon) => renglon.textContent?.includes('Lateral'),
    );
    expect(renglonesLateral.length).toBe(1);
    expect(renglonesLateral[0].textContent).toContain('12');
    expect(renglonesLateral[0].textContent).toContain('16');
    expect(renglonesLateral[0].textContent).toContain('20');
  });

  it('no dibuja emisores por defecto y los enciende desde el control (S4)', () => {
    const { fixture, plano } = montarConFixture(redDensa(14000));
    const svg = plano.querySelector('[data-plano-svg]') as SVGSVGElement;

    // Con el plano en su lectura por defecto no hay ni un punto de emisor.
    expect(svg.querySelectorAll('[data-emisor]').length).toBe(0);

    // El encabezado sigue mostrando la cifra real del payload, no la dibujada.
    const encabezado = plano.querySelector('[data-plano-red]') as HTMLElement;
    expect(encabezado.textContent).toContain('14000 emisores');

    const control = plano.querySelector('[data-toggle-emisores]') as HTMLButtonElement;
    expect(control.getAttribute('aria-pressed')).toBe('false');
    control.click();
    fixture.detectChanges();

    const dibujados = svg.querySelectorAll('[data-emisor]').length;
    expect(dibujados).toBeGreaterThan(0);
    expect(dibujados).toBeLessThan(600);
    expect(control.getAttribute('aria-pressed')).toBe('true');

    // La nota de densidad dice cuántos se dibujan y cuántos usa el cómputo.
    const densidad = plano.querySelector('[data-emisores-densidad]') as HTMLElement;
    expect(densidad.textContent).toContain(String(dibujados));
    expect(densidad.textContent).toContain('14000');

    // Se pueden volver a apagar.
    control.click();
    fixture.detectChanges();
    expect(svg.querySelectorAll('[data-emisor]').length).toBe(0);
  });

  it('prioriza matriz, secundaria y laterales con zonas de color visible (S4)', () => {
    const { plano } = montarConFixture(RED);
    const svg = plano.querySelector('[data-plano-svg]') as SVGSVGElement;

    const principal = svg.querySelector('[data-tramo-tipo="principal"]') as SVGPolylineElement;
    const lateral = svg.querySelector('[data-tramo-tipo="lateral"]') as SVGPolylineElement;
    expect(principal).not.toBeNull();
    expect(lateral).not.toBeNull();

    // La matriz manda: más gruesa que la tubería secundaria y que el lateral.
    const anchoPrincipal = Number(principal.getAttribute('stroke-width'));
    const anchoLateral = Number(lateral.getAttribute('stroke-width'));
    expect(anchoPrincipal).toBeGreaterThan(anchoLateral);

    // El relleno de las zonas deja ver el color del producto (S2, S4).
    const zona = svg.querySelector('[data-zona]') as SVGPolygonElement;
    expect(Number(zona.getAttribute('fill-opacity'))).toBeGreaterThanOrEqual(0.5);
  });

  it('baja la densidad de líneas cuando hay muchísimos laterales (S4)', () => {
    const { plano } = montarConFixture(redConLaterales(250));
    const svg = plano.querySelector('[data-plano-svg]') as SVGSVGElement;

    const lateral = svg.querySelector('[data-tramo-tipo="lateral"]') as SVGPolylineElement;
    expect(lateral).not.toBeNull();
    expect(Number(lateral.getAttribute('stroke-opacity'))).toBeLessThan(1);

    // La zona y su color siguen visibles debajo de la red densa.
    const zona = svg.querySelector('[data-zona]') as SVGPolygonElement;
    expect(Number(zona.getAttribute('fill-opacity'))).toBeGreaterThanOrEqual(0.5);
  });

  it('sin red mantiene el mensaje de plano vacío (S4)', () => {
    const plano = montar({ nodos: [], tramos: [], emisores: [] });
    expect(plano.querySelector('[data-plano-svg]')).toBeNull();
    expect(plano.querySelector('[data-plano-vacio]')).not.toBeNull();
  });
});
