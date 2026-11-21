import { Component } from '@angular/core';

/** Trust strip under the grid: calculation engine, standards and sync status. */
@Component({
  selector: 'app-technical-footnote',
  template: `
    <div
      class="bg-surface-container-lowest rounded-xl px-space-lg py-space-md shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-space-sm"
    >
      <div class="flex items-start gap-space-sm">
        <span class="material-symbols-outlined text-[20px] text-primary" aria-hidden="true"
          >verified_user</span
        >
        <div>
          <p class="text-label-md text-on-surface">Motor de Cálculo Agronómico Activo</p>
          <p class="text-body-sm text-on-surface-variant">
            Norma Hazen-Williams para pérdidas de carga y coeficientes Kc FAO-56 aplicados en tiempo
            real.
          </p>
        </div>
      </div>
      <div class="flex items-center gap-1.5 text-label-sm text-on-surface-variant shrink-0">
        <span class="material-symbols-outlined text-[18px] text-secondary" aria-hidden="true"
          >cloud_done</span
        >
        Almacenamiento en la nube sincronizado
      </div>
    </div>
  `,
})
export class TechnicalFootnote {}
