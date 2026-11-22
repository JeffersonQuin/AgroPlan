import { Component, computed, input, signal, viewChild, ElementRef } from '@angular/core';
import { formatearNumero, materialTramo } from '../../formato-informe';
import {
  BloqueInformeApi,
  RedInformeApi,
  SectorInformeApi,
  SistemaInformeApi,
  TerrenoResumen,
} from '../../models/resumen.model';

/** Marco del plano en unidades SVG. */
const MARCO = { ancho: 900, alto: 520, margen: 56 } as const;
const ZOOM_MIN = 0.5;
const ZOOM_MAX = 4;
const PASO_ZOOM = 1.25;

/**
 * Presupuesto de goteros visibles a zoom 1.
 *
 * Con 14.000 emisores el plano se vuelve una masa azul; se dibuja uno de cada N y N
 * baja al acercar. La cifra del payload no cambia: el encabezado y la nota de
 * densidad siguen mostrando el total real.
 */
const UMBRAL_EMISORES = 420;

/** Diámetros que entran en un renglón de leyenda antes de agrupar el resto. */
const MAX_DIAMETROS_LEYENDA = 4;

const ALTO_ETIQUETA_ZONA = 22;
const ALTO_ETIQUETA_SECTOR = 18;

interface PuntoSvg {
  x: number;
  y: number;
}

interface Rect {
  x: number;
  y: number;
  ancho: number;
  alto: number;
}

interface EtiquetaDibujo extends Rect {
  texto: string;
  fondo: string;
  borde: string;
  colorTexto: string;
  textoY: number;
}

interface ZonaDibujo {
  id: string;
  puntos: string;
  color: string;
  etiqueta: EtiquetaDibujo;
}

interface SectorDibujo {
  id: string;
  puntos: string;
  etiqueta: EtiquetaDibujo;
}

interface TramoDibujo {
  id: string;
  puntos: string;
  color: string;
  ancho: number;
}

interface NodoDibujo {
  id: string;
  tipo: string;
  x: number;
  y: number;
}

interface LeyendaTramo {
  clave: string;
  texto: string;
  color: string;
  ancho: number;
}

interface Dibujo {
  terreno: string | null;
  zonas: ZonaDibujo[];
  sectores: SectorDibujo[];
  tramos: TramoDibujo[];
  nodos: NodoDibujo[];
  emisores: PuntoSvg[];
  leyenda: LeyendaTramo[];
}

const COLOR_TRAMO: Record<string, string> = {
  principal: '#1d4ed8',
  secundario: '#2563eb',
  lateral: '#0284c7',
  conexion: '#0ea5e9',
};

const ANCHO_TRAMO: Record<string, number> = {
  principal: 4.5,
  secundario: 3.2,
  lateral: 2.2,
  conexion: 1.6,
};

/** Nombre de cada tipo de tramo en la leyenda; el principal es la matriz del cabezal. */
const NOMBRE_TRAMO: Record<string, string> = {
  principal: 'Matriz (tubería principal)',
  secundario: 'Tubería secundaria',
  lateral: 'Lateral de goteo',
  conexion: 'Conexión',
};

/**
 * Plano 2D del informe (S4).
 *
 * Orden de lectura, de abajo hacia arriba: el polígono real del terreno, las zonas de
 * cultivo (relleno con el color del bloque y su etiqueta), los sectores (contorno
 * punteado + etiqueta), la red, los goteros y los nodos.
 *
 * Todo sale de `terreno`, `bloques`, `sectores` y `red`: no hay coordenadas inventadas.
 * Sin red, el componente muestra un mensaje en vez de un plano vacío dibujado.
 *
 * Conserva las herramientas del paso 1: zoom, centrado, cuadrícula y paneo con el
 * puntero sobre el fondo.
 */
@Component({
  selector: 'app-plano-red',
  templateUrl: './plano-red.html',
})
export class PlanoRed {
  readonly red = input.required<RedInformeApi>();
  readonly bloques = input<BloqueInformeApi[]>([]);
  readonly sectores = input<SectorInformeApi[]>([]);
  readonly sistema = input<SistemaInformeApi | null>(null);
  /** Terreno del paso 1: su `geometria` es el contorno real que dibujó el cliente. */
  readonly terreno = input<TerrenoResumen | null>(null);

  private readonly lienzo = viewChild<ElementRef<SVGSVGElement>>('lienzo');
  private readonly zoom = signal(1);
  private readonly pan = signal<PuntoSvg>({ x: 0, y: 0 });
  private readonly cuadricula = signal(true);
  private readonly arrastrando = signal(false);
  private readonly punteroInicial = signal<PuntoSvg>({ x: 0, y: 0 });
  private readonly panInicial = signal<PuntoSvg>({ x: 0, y: 0 });

  protected readonly centro = {
    x: MARCO.ancho / 2,
    y: MARCO.alto / 2,
  } as const;

  /** `true` cuando la corrida no generó red: sin tramos, nodos ni emisores no hay plano. */
  protected readonly vacio = computed(() => {
    const red = this.red();
    return red.tramos.length === 0 && red.nodos.length === 0 && red.emisores.length === 0;
  });

  protected readonly transformacion = computed(() => {
    const zoom = this.zoom();
    const pan = this.pan();
    const x = pan.x + this.centro.x * (1 - zoom);
    const y = pan.y + this.centro.y * (1 - zoom);
    return `translate(${x.toFixed(2)}, ${y.toFixed(2)}) scale(${zoom.toFixed(3)})`;
  });

  protected readonly zoomLabel = computed(() => `${Math.round(this.zoom() * 100)}%`);

  /** Goteros totales del payload: la cifra que el plano nunca cambia. */
  protected readonly emisoresTotales = computed(() =>
    this.red().emisores.reduce((total, tramo) => total + tramo.puntos.length, 0),
  );

  protected readonly dibujo = computed<Dibujo>(() => {
    const red = this.red();
    const sectores = this.sectores();
    const bloques = this.bloques();
    const terreno = this.terreno();

    const puntos: [number, number][] = [];
    for (const vertice of terreno?.geometria.vertices ?? []) puntos.push([vertice.x, vertice.y]);
    for (const tramo of red.tramos) for (const punto of tramo.puntos) puntos.push(punto);
    for (const emisores of red.emisores) for (const punto of emisores.puntos) puntos.push(punto);
    for (const nodo of red.nodos) puntos.push([nodo.geometria.x, nodo.geometria.y]);
    for (const bloque of bloques) for (const punto of bloque.poligono.anillo) puntos.push(punto);
    for (const sector of sectores) for (const punto of sector.poligono.anillo) puntos.push(punto);

    if (puntos.length === 0) {
      return {
        terreno: null,
        zonas: [],
        sectores: [],
        tramos: [],
        nodos: [],
        emisores: [],
        leyenda: [],
      };
    }

    let minX = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;
    for (const [x, y] of puntos) {
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    }
    const anchoM = Math.max(maxX - minX, 1);
    const altoM = Math.max(maxY - minY, 1);
    const utilAncho = MARCO.ancho - MARCO.margen * 2;
    const utilAlto = MARCO.alto - MARCO.margen * 2;
    const escala = Math.min(utilAncho / anchoM, utilAlto / altoM);
    const origenX = MARCO.margen + (utilAncho - anchoM * escala) / 2;
    const origenY = MARCO.margen + (utilAlto - altoM * escala) / 2 + altoM * escala;

    const proyectar = (punto: [number, number]): PuntoSvg => ({
      x: origenX + (punto[0] - minX) * escala,
      y: origenY - (punto[1] - minY) * escala,
    });
    const poligono = (anillo: [number, number][]): string =>
      anillo
        .map((punto) => {
          const svg = proyectar(punto);
          return `${svg.x.toFixed(1)},${svg.y.toFixed(1)}`;
        })
        .join(' ');
    const centroDe = (anillo: [number, number][], centroide: PuntoSvg | null): PuntoSvg => {
      if (centroide !== null) return proyectar([centroide.x, centroide.y]);
      return anillo.reduce(
        (acumulado, punto) => {
          const svg = proyectar(punto);
          return {
            x: acumulado.x + svg.x / anillo.length,
            y: acumulado.y + svg.y / anillo.length,
          };
        },
        { x: 0, y: 0 },
      );
    };

    // Las etiquetas de zona y de sector se reparten para no taparse entre sí: la
    // primera ocupa el centroide y las que chocan bajan (o se corren a la derecha).
    const ocupados: Rect[] = [];

    const zonasDibujo: ZonaDibujo[] = bloques.map((bloque) => {
      const texto = textoDeZona(bloque);
      const ancho = anchoEtiqueta(texto);
      const centro = centroDe(bloque.poligono.anillo, bloque.centroide);
      const etiqueta = crearEtiqueta(ocupados, centro, texto, ancho, ALTO_ETIQUETA_ZONA, {
        fondo: '#ffffff',
        borde: bloque.color,
        colorTexto: '#0f172a',
      });
      return {
        id: bloque.id,
        puntos: poligono(bloque.poligono.anillo),
        color: bloque.color,
        etiqueta,
      };
    });

    const sectoresDibujo: SectorDibujo[] = sectores.map((sector) => {
      const etiquetaTexto = sector.etiqueta ?? `Sector ${sector.numero}`;
      const ancho = anchoEtiqueta(etiquetaTexto);
      const centro = centroDe(sector.poligono.anillo, null);
      const etiqueta = crearEtiqueta(
        ocupados,
        centro,
        etiquetaTexto,
        ancho,
        ALTO_ETIQUETA_SECTOR,
        { fondo: '#065f46', borde: '#065f46', colorTexto: '#ffffff' },
      );
      return {
        id: sector.id,
        puntos: poligono(sector.poligono.anillo),
        etiqueta,
      };
    });

    const tramosDibujo: TramoDibujo[] = red.tramos.map((tramo) => ({
      id: tramo.id,
      puntos: tramo.puntos
        .map((punto) => {
          const svg = proyectar(punto);
          return `${svg.x.toFixed(1)},${svg.y.toFixed(1)}`;
        })
        .join(' '),
      color: COLOR_TRAMO[tramo.tipo] ?? '#0284c7',
      ancho: ANCHO_TRAMO[tramo.tipo] ?? 2,
    }));

    const nodosDibujo: NodoDibujo[] = red.nodos.map((nodo) => {
      const svg = proyectar([nodo.geometria.x, nodo.geometria.y]);
      return { id: nodo.id, tipo: nodo.tipo, x: svg.x, y: svg.y };
    });

    const emisores = red.emisores.flatMap((tramo) =>
      tramo.puntos.map((punto) => proyectar(punto)),
    );

    return {
      terreno: terreno === null ? null : poligono(verticesDelTerreno(terreno)),
      zonas: zonasDibujo,
      sectores: sectoresDibujo,
      tramos: tramosDibujo,
      nodos: nodosDibujo,
      emisores,
      leyenda: leyendaDeTramos(red),
    };
  });

  /**
   * Uno de cada `paso` goteros: el paso baja al acercar, así el zoom recupera detalle
   * sin cambiar la cifra real del encabezado.
   */
  private readonly pasoEmisores = computed(() => {
    const total = this.dibujo().emisores.length;
    if (total <= UMBRAL_EMISORES) return 1;
    return Math.max(1, Math.ceil(total / (UMBRAL_EMISORES * this.zoom())));
  });

  protected readonly emisoresVisibles = computed(() => {
    const emisores = this.dibujo().emisores;
    const paso = this.pasoEmisores();
    if (paso <= 1) return emisores;
    return emisores.filter((_, indice) => indice % paso === 0);
  });

  protected readonly emisoresOcultos = computed(
    () => this.emisoresTotales() - this.emisoresVisibles().length,
  );

  protected readonly radioEmisor = computed(() => (this.pasoEmisores() > 1 ? 1.5 : 2.4));

  protected readonly totalTuberia = computed(() =>
    this.red().tramos.reduce((total, tramo) => total + tramo.longitud_m, 0),
  );

  // ------------------------------------------------------------------- //
  // Herramientas del plano
  // ------------------------------------------------------------------- //

  protected alternarCuadricula(): void {
    this.cuadricula.update((visible) => !visible);
  }

  protected acercar(): void {
    this.zoom.update((zoom) => Math.min(ZOOM_MAX, Number((zoom * PASO_ZOOM).toFixed(3))));
  }

  protected alejar(): void {
    this.zoom.update((zoom) => Math.max(ZOOM_MIN, Number((zoom / PASO_ZOOM).toFixed(3))));
  }

  protected centrar(): void {
    this.zoom.set(1);
    this.pan.set({ x: 0, y: 0 });
  }

  protected onPointerDown(event: PointerEvent): void {
    const punto = this.aSvg(event);
    if (punto === null) return;
    (event.target as Element).setPointerCapture?.(event.pointerId);
    this.punteroInicial.set(punto);
    this.panInicial.set(this.pan());
    this.arrastrando.set(true);
  }

  protected onPointerMove(event: PointerEvent): void {
    if (!this.arrastrando()) return;
    const punto = this.aSvg(event);
    if (punto === null) return;
    const inicio = this.punteroInicial();
    const pan = this.panInicial();
    this.pan.set({
      x: Number((pan.x + punto.x - inicio.x).toFixed(2)),
      y: Number((pan.y + punto.y - inicio.y).toFixed(2)),
    });
  }

  protected onPointerUp(): void {
    this.arrastrando.set(false);
  }

  private aSvg(event: PointerEvent): PuntoSvg | null {
    const svg = this.lienzo()?.nativeElement;
    if (svg === undefined) return null;
    const matriz = svg.getScreenCTM();
    if (matriz === null) return null;
    const punto = new DOMPoint(event.clientX, event.clientY).matrixTransform(matriz.inverse());
    return { x: punto.x, y: punto.y };
  }

  protected etiquetaNodo(nodo: NodoDibujo): string {
    const etiquetas: Record<string, string> = {
      tanque: 'Tanque',
      bomba: 'Bomba',
      cabezal: 'Cabezal',
      valvula: 'Válvula',
      derivacion: 'Derivación',
      hidrante: 'Hidrante',
    };
    return etiquetas[nodo.tipo] ?? nodo.tipo;
  }

  protected esValvula(nodo: NodoDibujo): boolean {
    return nodo.tipo === 'valvula';
  }

  protected esTanque(nodo: NodoDibujo): boolean {
    return nodo.tipo === 'tanque';
  }
}

/** Vértices del terreno como anillo cerrado para el `polygon` del SVG. */
function verticesDelTerreno(terreno: TerrenoResumen): [number, number][] {
  return terreno.geometria.vertices.map((vertice) => [vertice.x, vertice.y] as [number, number]);
}

/** Etiqueta de la zona: nombre y porcentaje; sin porcentaje, el área real. */
function textoDeZona(bloque: BloqueInformeApi): string {
  const nombre = bloque.nombre ?? bloque.cultivo_codigo;
  if (bloque.porcentaje !== null && Number.isFinite(bloque.porcentaje)) {
    return `${nombre} · ${formatearNumero(bloque.porcentaje)}%`;
  }
  return `${nombre} · ${formatearNumero(bloque.area_m2)} m²`;
}

/** Ancho estimado del chip a partir del texto, acotado al ancho del marco. */
function anchoEtiqueta(texto: string): number {
  return Math.min(Math.max(Math.round(texto.length * 6.1) + 18, 54), MARCO.ancho / 2);
}

function choca(a: Rect, b: Rect): boolean {
  return (
    a.x < b.x + b.ancho && a.x + a.ancho > b.x && a.y < b.y + b.alto && a.y + a.alto > b.y
  );
}

/**
 * Coloca un chip en el centroide sin tapar las etiquetas ya puestas.
 *
 * Primero se intenta centrado; si choca, baja en saltos de su propio alto y, si se
 * acaba el alto del marco, se corre a la derecha. El rectángulo queda reservado para
 * las etiquetas siguientes.
 */
function crearEtiqueta(
  ocupados: Rect[],
  centro: PuntoSvg,
  texto: string,
  ancho: number,
  alto: number,
  estilo: { fondo: string; borde: string; colorTexto: string },
): EtiquetaDibujo {
  const ubicar = (desplazamiento: number, corrimiento = 0): Rect => ({
    x: Math.min(Math.max(4, centro.x - ancho / 2 + corrimiento), MARCO.ancho - ancho - 4),
    y: Math.min(Math.max(4, centro.y - alto / 2 + desplazamiento), MARCO.alto - alto - 4),
    ancho,
    alto,
  });

  let candidato = ubicar(0);
  for (let vuelta = 1; vuelta <= 8 && ocupados.some((rect) => choca(rect, candidato)); vuelta++) {
    candidato = ubicar(vuelta * (alto + 4));
  }
  for (let vuelta = 1; vuelta <= 4 && ocupados.some((rect) => choca(rect, candidato)); vuelta++) {
    candidato = ubicar(0, vuelta * (ancho / 2 + 6));
  }
  ocupados.push(candidato);

  return {
    ...candidato,
    texto,
    ...estilo,
    textoY: candidato.y + alto / 2 + 4,
  };
}

/**
 * Leyenda de la red: un renglón por tipo de tramo con sus diámetros agrupados.
 *
 * Con un solo diámetro conserva el texto histórico "PVC Ø32 mm · Tubería principal";
 * con varios los lista (hasta `MAX_DIAMETROS_LEYENDA`) y resume el resto.
 */
function leyendaDeTramos(red: RedInformeApi): LeyendaTramo[] {
  const porTipo = new Map<string, number[]>();
  for (const tramo of red.tramos) {
    const diametros = porTipo.get(tramo.tipo) ?? [];
    if (!diametros.includes(tramo.diametro_mm)) diametros.push(tramo.diametro_mm);
    porTipo.set(tramo.tipo, diametros);
  }

  return Array.from(porTipo.entries()).map(([tipo, diametros]) => {
    const ordenados = [...diametros].sort((a, b) => a - b);
    const visibles = ordenados.slice(0, MAX_DIAMETROS_LEYENDA);
    const restantes = ordenados.length - visibles.length;
    const diametrosTexto =
      visibles.length === 1
        ? `Ø${visibles[0]} mm`
        : `Ø${visibles.join(' mm, ')} mm${restantes > 0 ? ` (+${restantes})` : ''}`;
    return {
      clave: tipo,
      texto: `${materialTramo(tipo)} ${diametrosTexto} · ${NOMBRE_TRAMO[tipo] ?? tipo}`,
      color: COLOR_TRAMO[tipo] ?? '#0284c7',
      ancho: ANCHO_TRAMO[tipo] ?? 2,
    };
  });
}
