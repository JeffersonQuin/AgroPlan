import { Component, ElementRef, computed, inject, signal, viewChild } from '@angular/core';
import { TerrainStore } from '../../state/terrain.store';
import { Vertice, cotasDesdeArrastre } from '../../utils/terrain-geometry';

/** Frame the mockup drew the parcel in, in SVG units. */
const MARCO = { x0: 130, x1: 610, y0: 70, y1: 420 } as const;
const CENTRO = { x: (MARCO.x0 + MARCO.x1) / 2, y: (MARCO.y0 + MARCO.y1) / 2 } as const;
const ETIQUETA_ANCHO = 84;
const ETIQUETA_ALTO = 24;
const SEPARACION_ETIQUETA = 26;
const ZOOM_MIN = 0.5;
const ZOOM_MAX = 4;
const PASO_ZOOM = 1.25;

interface PuntoSvg { x: number; y: number; }
interface Lado { etiqueta: string; cajaX: number; cajaY: number; textoX: number; textoY: number; }

interface Dibujo {
  puntos: string;
  vertices: PuntoSvg[];
  lados: Lado[];
  escala: number;
  origenX: number;
  origenY: number;
}

/**
 * Technical drawing of the parcel.
 *
 * It projects the same vertices that `TerrainStore.aPayload()` sends to the
 * backend, so what the user sees is exactly the terrain that gets saved. The
 * figure is centered in the frame, can be zoomed and panned, and its vertices are
 * draggable: moving one rewrites the cota (or cotas) that define it.
 */
@Component({
  selector: 'app-terrain-canvas',
  templateUrl: './terrain-canvas.html',
})
export class TerrainCanvas {
  protected readonly store = inject(TerrainStore);
  private readonly lienzo = viewChild<ElementRef<SVGSVGElement>>('lienzo');
  private readonly figura = viewChild<ElementRef<SVGGElement>>('figura');

  private readonly arrastrando = signal<number | null>(null);
  private readonly panInicial = signal<PuntoSvg>({ x: 0, y: 0 });
  private readonly punteroInicial = signal<PuntoSvg>({ x: 0, y: 0 });

  protected readonly zoom = signal(1);
  protected readonly pan = signal<PuntoSvg>({ x: 0, y: 0 });
  protected readonly cuadricula = signal(true);

  /** Transformación que aplica zoom y paneo alrededor del centro del marco. */
  protected readonly transformacion = computed(() => {
    const zoom = this.zoom();
    const pan = this.pan();
    const x = pan.x + CENTRO.x * (1 - zoom);
    const y = pan.y + CENTRO.y * (1 - zoom);
    return `translate(${x.toFixed(2)}, ${y.toFixed(2)}) scale(${zoom.toFixed(3)})`;
  });

  protected readonly zoomLabel = computed(() => `${Math.round(this.zoom() * 100)}%`);

  protected readonly dibujo = computed<Dibujo>(() => {
    const vertices = this.store.vertices();
    const anchoM = Math.max(...vertices.map((vertice) => vertice.x), 1);
    const altoM = Math.max(...vertices.map((vertice) => vertice.y), 1);
    const utilAncho = MARCO.x1 - MARCO.x0;
    const utilAlto = MARCO.y1 - MARCO.y0;
    const escala = Math.min(utilAncho / anchoM, utilAlto / altoM);

    // Centrada en el marco, en los dos ejes.
    const margenX = (utilAncho - anchoM * escala) / 2;
    const margenY = (utilAlto - altoM * escala) / 2;
    const origenX = MARCO.x0 + margenX;
    const origenY = MARCO.y0 + margenY + altoM * escala;

    const puntos = vertices.map((vertice) => ({
      x: origenX + vertice.x * escala,
      y: origenY - vertice.y * escala,
    }));

    const centro = {
      x: puntos.reduce((suma, punto) => suma + punto.x, 0) / puntos.length,
      y: puntos.reduce((suma, punto) => suma + punto.y, 0) / puntos.length,
    };

    const lados: Lado[] = vertices.map((vertice, indice) => {
      const siguiente = vertices[(indice + 1) % vertices.length];
      const desde = puntos[indice];
      const hasta = puntos[(indice + 1) % puntos.length];
      const medio = { x: (desde.x + hasta.x) / 2, y: (desde.y + hasta.y) / 2 };

      // La etiqueta se separa del centro del polígono para no tapar el dibujo.
      const dx = medio.x - centro.x;
      const dy = medio.y - centro.y;
      const largo = Math.hypot(dx, dy) || 1;
      const x = medio.x + (dx / largo) * SEPARACION_ETIQUETA;
      const y = medio.y + (dy / largo) * SEPARACION_ETIQUETA;

      return {
        etiqueta: `${distancia(vertice, siguiente).toFixed(2)} m`,
        cajaX: x - ETIQUETA_ANCHO / 2,
        cajaY: y - ETIQUETA_ALTO / 2,
        textoX: x,
        textoY: y + 4,
      };
    });

    return {
      puntos: puntos.map((punto) => `${punto.x.toFixed(1)},${punto.y.toFixed(1)}`).join(' '),
      vertices: puntos,
      lados,
      escala,
      origenX,
      origenY,
    };
  });

  // ------------------------------------------------------------------- //
  // Herramientas del croquis
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

  // ------------------------------------------------------------------- //
  // Arrastre: vértices o paneo
  // ------------------------------------------------------------------- //

  /** Un vértice se arrastra: sus coordenadas se traducen de vuelta a cotas. */
  protected onPointerDown(indice: number, event: PointerEvent): void {
    event.preventDefault();
    event.stopPropagation();
    (event.target as Element).setPointerCapture?.(event.pointerId);
    this.arrastrando.set(indice);
  }

  /** Arrastrar el fondo mueve la vista. */
  protected onFondoPointerDown(event: PointerEvent): void {
    if (this.arrastrando() !== null) return;
    const punto = this.aSvg(event);
    if (punto === null) return;
    (event.target as Element).setPointerCapture?.(event.pointerId);
    this.punteroInicial.set(punto);
    this.panInicial.set(this.pan());
    this.arrastrando.set(-1);
  }

  protected onPointerMove(event: PointerEvent): void {
    const indice = this.arrastrando();
    if (indice === null) return;

    if (indice === -1) {
      const punto = this.aSvg(event);
      if (punto === null) return;
      const inicio = this.punteroInicial();
      const pan = this.panInicial();
      this.pan.set({
        x: Number((pan.x + punto.x - inicio.x).toFixed(2)),
        y: Number((pan.y + punto.y - inicio.y).toFixed(2)),
      });
      return;
    }

    const punto = this.aVertice(event);
    if (punto === null) return;
    this.mover(indice, punto.x, punto.y);
  }

  protected onPointerUp(): void {
    this.arrastrando.set(null);
  }

  /** Punto del puntero en el espacio del SVG, sin zoom ni paneo. */
  private aSvg(event: PointerEvent): PuntoSvg | null {
    const svg = this.lienzo()?.nativeElement;
    if (svg === undefined) return null;
    const matriz = svg.getScreenCTM();
    if (matriz === null) return null;
    const punto = new DOMPoint(event.clientX, event.clientY).matrixTransform(matriz.inverse());
    return { x: punto.x, y: punto.y };
  }

  /** Punto del puntero en metros, descontando el zoom y el paneo de la figura. */
  private aVertice(event: PointerEvent): PuntoSvg | null {
    const figura = this.figura()?.nativeElement;
    const dibujo = this.dibujo();
    if (figura === undefined) return null;
    const matriz = figura.getScreenCTM();
    if (matriz === null) return null;

    const punto = new DOMPoint(event.clientX, event.clientY).matrixTransform(matriz.inverse());
    return {
      x: Math.max(0, Math.round(((punto.x - dibujo.origenX) / dibujo.escala) * 10) / 10),
      y: Math.max(0, Math.round((((dibujo.origenY - punto.y) / dibujo.escala) || 0) * 10) / 10),
    };
  }

  private mover(indice: number, x: number, y: number): void {
    const state = this.store.state();
    const cambios = cotasDesdeArrastre(state.shape, state.dimensions, indice, x, y);
    const entradas = Object.entries(cambios) as [keyof typeof state.dimensions, number][];
    for (const [cota, valor] of entradas) this.store.setDimension(cota, valor);
  }
}

function distancia(a: Vertice, b: Vertice): number {
  return Math.hypot(b.x - a.x, b.y - a.y);
}
