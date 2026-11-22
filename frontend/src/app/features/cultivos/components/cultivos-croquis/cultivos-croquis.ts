import { Component, computed, inject } from '@angular/core';
import { CultivosStore } from '../../state/cultivos.store';

const MARCO = { ancho: 740, alto: 480, margen: 40 } as const;

interface BloqueDibujado {
  id: string;
  puntos: string;
  color: string;
  etiqueta: string;
  porcentaje: number;
}

/**
 * Drawing of the crop blocks.
 *
 * The polygons come from the backend (`poligono.anillo` in metres); here they are
 * only projected into the frame, so the picture is the real distribution the motor
 * calculated, not a sketch.
 */
@Component({
  selector: 'app-cultivos-croquis',
  templateUrl: './cultivos-croquis.html',
})
export class CultivosCroquis {
  protected readonly store = inject(CultivosStore);

  /** Centro del bloque en el SVG, para colgar la etiqueta. */
  protected centro(bloque: BloqueDibujado): { x: number; y: number } {
    const puntos = bloque.puntos.split(' ').map((par) => par.split(',').map(Number));
    return {
      x: puntos.reduce((suma, [x]) => suma + x, 0) / puntos.length,
      y: puntos.reduce((suma, [, y]) => suma + y, 0) / puntos.length,
    };
  }

  protected readonly bloques = computed<BloqueDibujado[]>(() => {
    const bloques = this.store.bloques();
    if (bloques.length === 0) return [];

    const puntos = bloques.flatMap((bloque) => bloque.poligono.anillo);
    const xs = puntos.map(([x]) => x);
    const ys = puntos.map(([, y]) => y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const anchoM = Math.max(maxX - minX, 1);
    const altoM = Math.max(maxY - minY, 1);

    const utilAncho = MARCO.ancho - MARCO.margen * 2;
    const utilAlto = MARCO.alto - MARCO.margen * 2;
    const escala = Math.min(utilAncho / anchoM, utilAlto / altoM);
    const margenX = MARCO.margen + (utilAncho - anchoM * escala) / 2;
    const margenY = MARCO.margen + (utilAlto - altoM * escala) / 2;

    return bloques.map((bloque) => ({
      id: bloque.id,
      etiqueta: bloque.etiqueta ?? bloque.cultivo_codigo,
      porcentaje: bloque.porcentaje,
      color:
        this.store
          .opcionesCultivo()
          .find((opcion) => opcion.value === bloque.cultivo_codigo)?.color ?? '#4CAF50',
      puntos: bloque.poligono.anillo
        .map(
          ([x, y]) =>
            `${(margenX + (x - minX) * escala).toFixed(1)},${(margenY + (maxY - y) * escala).toFixed(1)}`,
        )
        .join(' '),
    }));
  });
}
