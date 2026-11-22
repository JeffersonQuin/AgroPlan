import { Component, computed, input } from '@angular/core';
import { Project, VerticeTerrenoApi } from '../../models/project.model';
import { PreviewFincaElParaiso } from './preview-finca-el-paraiso';
import { PreviewMiParcela } from './preview-mi-parcela';
import { PreviewParcelaNorte } from './preview-parcela-norte';

/** Card schematic canvas, in SVG user units. */
const ANCHO = 340;
const ALTO = 160;
const MARGEN = 16;

/**
 * Schematic over the card. The three reference projects keep the hand-drawn SVGs
 * of the mockup; a project with a saved terrain draws its real contour, and one
 * without terrain falls back to the empty state.
 */
@Component({
  selector: 'app-project-preview',
  imports: [PreviewMiParcela, PreviewParcelaNorte, PreviewFincaElParaiso],
  template: `
    @switch (project().preview) {
      @case ('parcela-norte') {
        <app-preview-parcela-norte [ariaLabel]="label()" />
      }
      @case ('finca-el-paraiso') {
        <app-preview-finca-el-paraiso [ariaLabel]="label()" />
      }
      @case ('mi-parcela') {
        <app-preview-mi-parcela [ariaLabel]="label()" />
      }
      @default {
        <svg
          class="w-full h-full select-none"
          [attr.viewBox]="'0 0 ' + ancho + ' ' + alto"
          role="img"
          [attr.aria-label]="label()"
        >
          @if (contorno(); as puntos) {
            <polygon [attr.points]="puntos" fill="#f8faf6" stroke="#166534" stroke-width="2" />
          } @else {
            <polygon
              points="20,15 315,15 260,145 20,145"
              fill="#f8faf6"
              stroke="#166534"
              stroke-dasharray="4 2"
              stroke-width="2"
            />
            <text
              x="170"
              y="85"
              text-anchor="middle"
              font-family="Inter"
              font-size="11"
              fill="#4b5563"
            >
              Sin terreno definido
            </text>
          }
        </svg>
      }
    }
  `,
})
export class ProjectPreview {
  readonly project = input.required<Project>();

  protected readonly ancho = ANCHO;
  protected readonly alto = ALTO;

  protected readonly label = computed(() => `Plano esquemático de ${this.project().name}`);

  /** The saved contour, scaled into the card canvas; `null` without terrain. */
  protected readonly contorno = computed(() => {
    const vertices = this.project().geometria?.vertices ?? [];
    return vertices.length >= 3 ? puntosDelContorno(vertices) : null;
  });
}

/**
 * Scales the saved vertices into the canvas, keeping the real proportions and
 * drawing `y` upwards as the terrain stores it.
 */
export function puntosDelContorno(vertices: VerticeTerrenoApi[]): string {
  const xs = vertices.map((vertice) => vertice.x);
  const ys = vertices.map((vertice) => vertice.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const anchoReal = maxX - minX || 1;
  const altoReal = maxY - minY || 1;

  const escala = Math.min((ANCHO - 2 * MARGEN) / anchoReal, (ALTO - 2 * MARGEN) / altoReal);
  const desplazadoX = (ANCHO - anchoReal * escala) / 2;
  const desplazadoY = (ALTO - altoReal * escala) / 2;

  return vertices
    .map((vertice) => {
      const x = desplazadoX + (vertice.x - minX) * escala;
      const y = desplazadoY + (maxY - vertice.y) * escala;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}
