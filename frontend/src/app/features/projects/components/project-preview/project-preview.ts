import { Component, computed, input } from '@angular/core';
import { Project } from '../../models/project.model';
import { PreviewFincaElParaiso } from './preview-finca-el-paraiso';
import { PreviewMiParcela } from './preview-mi-parcela';
import { PreviewParcelaNorte } from './preview-parcela-norte';

/**
 * Schematic over the card. The three reference projects use the hand-drawn
 * SVGs from the mockup, reproduced verbatim; a project created from the dialog
 * has no geometry yet and falls back to the empty state.
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
          viewBox="0 0 340 160"
          role="img"
          [attr.aria-label]="label()"
        >
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
        </svg>
      }
    }
  `,
})
export class ProjectPreview {
  readonly project = input.required<Project>();

  protected readonly label = computed(
    () => `Plano esquemático de ${this.project().name}`,
  );
}
