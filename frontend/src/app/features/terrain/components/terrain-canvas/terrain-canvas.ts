import { Component, computed, inject } from '@angular/core';
import { TerrainStore } from '../../state/terrain.store';
import { Vertice } from '../../utils/terrain-geometry';

/** Frame the mockup drew the parcel in, in SVG units. */
const MARCO = { x0: 130, x1: 610, y0: 70, y1: 420 } as const;
const ETIQUETA_ANCHO = 84;
const ETIQUETA_ALTO = 24;
const SEPARACION_ETIQUETA = 26;

interface Lado {
  etiqueta: string;
  cajaX: number;
  cajaY: number;
  textoX: number;
  textoY: number;
}

interface Dibujo {
  puntos: string;
  lados: Lado[];
  vacio: boolean;
}

/**
 * Technical drawing of the parcel.
 *
 * It projects the same vertices that `TerrainStore.aPayload()` sends to the
 * backend, so what the user sees is exactly the terrain that gets saved. The
 * frame stays fixed and the figure is scaled to fit, keeping metres square.
 */
@Component({
  selector: 'app-terrain-canvas',
  templateUrl: './terrain-canvas.html',
})
export class TerrainCanvas {
  protected readonly store = inject(TerrainStore);

  protected readonly dibujo = computed<Dibujo>(() => {
    const vertices = this.store.vertices();
    if (vertices.length < 3) return { puntos: '', lados: [], vacio: true };

    const anchoM = Math.max(...vertices.map((vertice) => vertice.x), 0);
    const altoM = Math.max(...vertices.map((vertice) => vertice.y), 0);
    const utilAncho = MARCO.x1 - MARCO.x0;
    const utilAlto = MARCO.y1 - MARCO.y0;
    const escala = Math.min(
      anchoM > 0 ? utilAncho / anchoM : utilAncho,
      altoM > 0 ? utilAlto / altoM : utilAlto,
    );

    // Centrado en el marco: la figura se apoya en el borde inferior.
    const margenX = (utilAncho - anchoM * escala) / 2;
    const puntos = vertices.map((vertice) => ({
      x: MARCO.x0 + margenX + vertice.x * escala,
      y: MARCO.y1 - vertice.y * escala,
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
      lados,
      vacio: false,
    };
  });
}

function distancia(a: Vertice, b: Vertice): number {
  return Math.hypot(b.x - a.x, b.y - a.y);
}
