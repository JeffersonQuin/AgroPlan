import { Component, computed, input, signal, viewChild, ElementRef } from '@angular/core';
import { materialTramo, textoTramo } from '../../formato-informe';
import {
  BloqueInformeApi,
  RedInformeApi,
  SectorInformeApi,
  SistemaInformeApi,
} from '../../models/resumen.model';

/** Marco del plano en unidades SVG. */
const MARCO = { ancho: 900, alto: 520, margen: 56 } as const;
const ZOOM_MIN = 0.5;
const ZOOM_MAX = 4;
const PASO_ZOOM = 1.25;

interface PuntoSvg {
  x: number;
  y: number;
}

interface SectorDibujo {
  id: string;
  puntos: string;
  color: string;
  etiqueta: string;
  centro: PuntoSvg;
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
  bloques: SectorDibujo[];
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

/**
 * Plano 2D del informe (S1, S10).
 *
 * Todo lo que se dibuja sale de `red` y de los polígonos de `bloques`/`sectores`:
 * los tramos son sus puntos reales, los goteros son los `emisores` derivados por el
 * backend y los nodos son el tanque, la bomba y las válvulas. No hay coordenadas
 * inventadas: sin red, el componente muestra un mensaje.
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

  protected readonly dibujo = computed<Dibujo>(() => {
    const red = this.red();
    const sectores = this.sectores();
    const bloques = this.bloques();

    const puntos: [number, number][] = [];
    for (const tramo of red.tramos) for (const punto of tramo.puntos) puntos.push(punto);
    for (const emisores of red.emisores) for (const punto of emisores.puntos) puntos.push(punto);
    for (const nodo of red.nodos) puntos.push([nodo.geometria.x, nodo.geometria.y]);
    for (const bloque of bloques) for (const punto of bloque.poligono.anillo) puntos.push(punto);
    for (const sector of sectores) for (const punto of sector.poligono.anillo) puntos.push(punto);

    if (puntos.length === 0) {
      return { bloques: [], sectores: [], tramos: [], nodos: [], emisores: [], leyenda: [] };
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

    const colorDeSector = (sector: SectorInformeApi): string => {
      for (const id of sector.cultivo_ids) {
        const bloque = bloques.find((candidato) => candidato.id === id);
        if (bloque !== undefined) return bloque.color;
      }
      return '#dcfce7';
    };

    const sectoresDibujo: SectorDibujo[] = sectores.map((sector) => {
      const anillo = sector.poligono.anillo;
      const centro = anillo.reduce(
        (acumulado, punto) => {
          const svg = proyectar(punto);
          return { x: acumulado.x + svg.x / anillo.length, y: acumulado.y + svg.y / anillo.length };
        },
        { x: 0, y: 0 },
      );
      return {
        id: sector.id,
        puntos: poligono(anillo),
        color: colorDeSector(sector),
        etiqueta: sector.etiqueta ?? `Sector ${sector.numero}`,
        centro,
      };
    });

    const bloquesDibujo: SectorDibujo[] = bloques.map((bloque) => {
      const anillo = bloque.poligono.anillo;
      const centro = anillo.reduce(
        (acumulado, punto) => {
          const svg = proyectar(punto);
          return { x: acumulado.x + svg.x / anillo.length, y: acumulado.y + svg.y / anillo.length };
        },
        { x: 0, y: 0 },
      );
      return {
        id: bloque.id,
        puntos: poligono(anillo),
        color: bloque.color,
        etiqueta: bloque.nombre ?? bloque.cultivo_codigo,
        centro,
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
      bloques: bloquesDibujo,
      sectores: sectoresDibujo,
      tramos: tramosDibujo,
      nodos: nodosDibujo,
      emisores,
      leyenda: leyendaDeTramos(red),
    };
  });

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

/** Leyenda dinámica: un ítem por combinación tipo + diámetro que traen los tramos. */
function leyendaDeTramos(red: RedInformeApi): LeyendaTramo[] {
  const vistos = new Map<string, LeyendaTramo>();
  for (const tramo of red.tramos) {
    const clave = `${tramo.tipo}-${tramo.diametro_mm}`;
    if (vistos.has(clave)) continue;
    vistos.set(clave, {
      clave,
      texto: `${materialTramo(tramo.tipo)} Ø${tramo.diametro_mm} mm · ${textoTramo(tramo.tipo)}`,
      color: COLOR_TRAMO[tramo.tipo] ?? '#0284c7',
      ancho: ANCHO_TRAMO[tramo.tipo] ?? 2,
    });
  }
  return Array.from(vistos.values());
}

