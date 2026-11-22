import { Component, output } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matAddCircleOutline,
  matLandscapeOutline,
  matMenuBookOutline,
} from '@ng-icons/material-symbols/outline';

/** Onboarding state shown when the user has no projects yet. */
@Component({
  selector: 'app-projects-empty-state',
  imports: [NgIcon],
  viewProviders: [provideIcons({ matAddCircleOutline, matLandscapeOutline, matMenuBookOutline })],
  template: `
    <div
      class="bg-surface-container-lowest rounded-xl p-space-xl text-center flex flex-col items-center justify-center py-16 shadow-sm"
    >
      <div
        class="w-16 h-16 rounded-full bg-surface-container-low flex items-center justify-center text-on-surface-variant mb-space-md"
      >
        <ng-icon name="matLandscapeOutline" size="32" aria-hidden="true" />
      </div>
      <h2 class="text-headline-md text-on-surface">Aún no tienes parcelas planificadas</h2>
      <p class="text-body-md text-on-surface-variant mt-1 max-w-md">
        Creá tu primer proyecto para dibujar el terreno, repartir cultivos y dimensionar el riego
        por goteo.
      </p>
      <div class="flex flex-wrap items-center justify-center gap-space-sm mt-space-lg">
        <button
          class="inline-flex items-center gap-space-xs bg-primary-container hover:bg-primary text-on-primary text-label-md px-space-lg py-2.5 rounded-lg transition-all shadow-sm"
          type="button"
          (click)="createFirst.emit()"
        >
          <ng-icon name="matAddCircleOutline" size="18" aria-hidden="true" />
          Crear mi primer proyecto agrícola
        </button>
        <button
          class="inline-flex items-center gap-space-xs bg-surface-container-low hover:bg-surface-container text-on-surface text-label-md px-space-lg py-2.5 rounded-lg transition-colors"
          type="button"
        >
          <ng-icon name="matMenuBookOutline" size="18" aria-hidden="true" />
          Ver proyecto de ejemplo
        </button>
      </div>
    </div>
  `,
})
export class ProjectsEmptyState {
  readonly createFirst = output<void>();
}
