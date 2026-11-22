import { Component, computed, inject } from '@angular/core';
import { CultivosStore } from '../../state/cultivos.store';

const MARCO = { ancho: 740, alto: 480, margen: 40 } as const;

/**
 * Drawing of the terrain from step 1.
 *
 * Step 2 does not distribute: the canvas shows the parcel as the user drew it, and the
 * division into sub-areas arrives in the final summary, when the agent answers.
 */
@Component({
  selector: 'app-cultivos-croquis',
  templateUrl: './cultivos-croquis.html',
})
export class CultivosCroquis {
  protected readonly store = inject(CultivosStore);

  protected readonly terreno = computed<string>(() => {
    const vertices = this.store.verticesTerreno();
    if (vertices.length < 3) return '';
    return proyectar(vertices.map((vertice): [number, number] => [vertice.x, vertice.y]));
  });
}

/** Proyecta el anillo del terreno en el marco del croquis. */
function proyectar(anillo: [number, number][]): string {
  const xs = anillo.map(([x]) => x);
  const ys = anillo.map(([, y]) => y);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const anchoM = Math.max(Math.max(...xs) - minX, 1);
  const altoM = Math.max(Math.max(...ys) - minY, 1);
  const escala = Math.min(
    (MARCO.ancho - MARCO.margen * 2) / anchoM,
    (MARCO.alto - MARCO.margen * 2) / altoM,
  );
  const margenX = MARCO.margen + (MARCO.ancho - MARCO.margen * 2 - anchoM * escala) / 2;
  const margenY = MARCO.margen + (MARCO.alto - MARCO.margen * 2 - altoM * escala) / 2;
  const maxY = Math.max(...ys);

  return anillo
    .map(
      ([x, y]) =>
        `${(margenX + (x - minX) * escala).toFixed(1)},${(
          margenY +
          (maxY - y) * escala
        ).toFixed(1)}`,
    )
    .join(' ');
}
