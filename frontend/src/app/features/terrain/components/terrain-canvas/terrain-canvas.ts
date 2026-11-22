import { Component, ElementRef, computed, inject, signal, viewChild } from '@angular/core';
import { TerrainStore } from '../../state/terrain.store';
import { Vertice, cotasDesdeArrastre } from '../../utils/terrain-geometry';

/** Frame the mockup drew the parcel in, in SVG units. */
const MARCO = { x0: 130, x1: 610, y0: 70, y1: 420 } as const;
const ETIQUETA_ANCHO = 84;
const ETIQUETA_ALTO = 24;
const SEPARACION_ETIQUETA = 26;
const SEPARACION_ARBOL = 16;

interface PuntoSvg { x: number; y: number; }
interface Lado { etiqueta: string; cajaX: number; cajaY: number; textoX: number; textoY: number; }
interface Arbol extends PuntoSvg { radio: number; claro: boolean; }

interface Dibujo {
  puntos: string;
  vertices: PuntoSvg[];
  lados: Lado[];
  arboles: Arbol[];
  escala: number;
  origenX: number;
  baseY: number;
}

/**
 * Technical drawing of the parcel.
 *
 * It projects the same vertices that `TerrainStore.aPayload()` sends to the
 * backend, so what the user sees is exactly the terrain that gets saved. Vertices
 * are draggable: moving one rewrites the cota (or cotas) that define it, and the
 * form, the summary and the saved payload follow.
 */
@Component({
  selector: 'app-terrain-canvas',
  templateUrl: './terrain-canvas.html',
})
export class TerrainCanvas {
  protected readonly store = inject(TerrainStore);
  private readonly lienzo = viewChild<ElementRef<SVGSVGElement>>('lienzo');
  private readonly arrastrando = signal<number | null>(null);

  protected readonly dibujo = computed<Dibujo>(() => {
    const vertices = this.store.vertices();
    const anchoM = Math.max(...vertices.map((vertice) => vertice.x), 1);
    const altoM = Math.max(...vertices.map((vertice) => vertice.y), 1);
    const utilAncho = MARCO.x1 - MARCO.x0;
    const utilAlto = MARCO.y1 - MARCO.y0;
    const escala = Math.min(utilAncho / anchoM, utilAlto / altoM);

    // Centrado en el marco: la figura se apoya en el borde inferior.
    const origenX = MARCO.x0 + (utilAncho - anchoM * escala) / 2;
    const baseY = MARCO.y1;

    const puntos = vertices.map((vertice) => ({
      x: origenX + vertice.x * escala,
      y: baseY - vertice.y * escala,
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
      arboles: arboles(puntos),
      escala,
      origenX,
      baseY,
    };
  });

  /** Un vértice se arrastra: sus coordenadas se traducen de vuelta a cotas. */
  protected onPointerDown(indice: number, event: PointerEvent): void {
    event.preventDefault();
    (event.target as Element).setPointerCapture?.(event.pointerId);
    this.arrastrando.set(indice);
  }

  protected onPointerMove(event: PointerEvent): void {
    const indice = this.arrastrando();
    const svg = this.lienzo()?.nativeElement;
    const dibujo = this.dibujo();
    if (indice === null || svg === undefined) return;

    const matriz = svg.getScreenCTM();
    if (matriz === null) return;

    const punto = new DOMPoint(event.clientX, event.clientY).matrixTransform(matriz.inverse());
    const x = Math.max(0, Math.round(((punto.x - dibujo.origenX) / dibujo.escala) * 10) / 10);
    const y = Math.max(0, Math.round(((dibujo.baseY - punto.y) / dibujo.escala) * 10) / 10);

    this.mover(indice, x, y);
  }

  protected onPointerUp(): void {
    this.arrastrando.set(null);
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

/** Árboles de la barrera viva: siguen los bordes superior e inferior de la figura. */
function arboles(puntos: PuntoSvg[]): Arbol[] {
  const minX = Math.min(...puntos.map((punto) => punto.x));
  const maxX = Math.max(...puntos.map((punto) => punto.x));
  const minY = Math.min(...puntos.map((punto) => punto.y));
  const maxY = Math.max(...puntos.map((punto) => punto.y));
  const cantidad = Math.max(2, Math.min(8, Math.floor((maxX - minX) / 65)));

  const fila = (y: number): Arbol[] =>
    Array.from({ length: cantidad }, (_, indice) => {
      const paso = (maxX - minX) / Math.max(cantidad - 1, 1);
      return {
        x: minX + paso * indice,
        y,
        radio: 9 + ((indice * 7) % 3) / 2,
        claro: indice % 2 === 1,
      };
    });

  return [...fila(minY - SEPARACION_ARBOL), ...fila(maxY + SEPARACION_ARBOL)];
}
