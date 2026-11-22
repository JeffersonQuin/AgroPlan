import { Component, input, output } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matAddCircleOutline,
  matFolderSharedOutline,
  matVisibilityOutline,
} from '@ng-icons/material-symbols/outline';

/** Page title, active-project counter and the primary actions. */
@Component({
  selector: 'app-projects-toolbar',
  imports: [NgIcon],
  viewProviders: [
    provideIcons({ matAddCircleOutline, matFolderSharedOutline, matVisibilityOutline }),
  ],
  template: `
    <div
      class="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-space-md"
    >
      <div class="flex items-center gap-space-md">
        <div
          class="w-10 h-10 rounded-lg bg-surface-container-low flex items-center justify-center text-primary-container"
        >
          <ng-icon name="matFolderSharedOutline" size="24" aria-hidden="true" />
        </div>
        <div>
          <div class="flex items-center gap-space-sm">
            <h1 class="text-headline-lg text-primary">Tus proyectos</h1>
            <span
              class="px-space-sm py-0.5 rounded-full bg-surface-container-high text-label-sm text-on-surface"
            >
              {{ activeCount() }} activos
            </span>
          </div>
          <p class="text-body-sm text-on-surface-variant">
            Gestión de parcelas, zonificación agronómica y trazado hidráulico
          </p>
        </div>
      </div>

      <div class="flex items-center flex-wrap gap-space-sm">
        <button
          class="inline-flex items-center gap-1.5 px-space-md py-2 rounded-lg bg-surface-bright text-on-surface-variant hover:bg-surface-container hover:text-on-surface text-label-sm transition-colors shadow-sm"
          type="button"
          [attr.aria-pressed]="emptyStateSimulated()"
          (click)="toggleEmptyState.emit()"
        >
          <ng-icon name="matVisibilityOutline" size="16" aria-hidden="true" />
          <span>{{ emptyStateSimulated() ? 'Ver proyectos reales' : 'Simular estado vacío' }}</span>
        </button>
        <button
          class="inline-flex items-center gap-space-xs bg-primary-container hover:bg-primary text-on-primary text-label-md px-space-lg py-2.5 rounded-lg transition-all shadow-sm"
          type="button"
          (click)="newProject.emit()"
        >
          <ng-icon name="matAddCircleOutline" size="18" aria-hidden="true" />
          <span>+ Nuevo proyecto</span>
        </button>
      </div>
    </div>
  `,
})
export class ProjectsToolbar {
  readonly activeCount = input.required<number>();
  readonly emptyStateSimulated = input(false);

  readonly newProject = output<void>();
  readonly toggleEmptyState = output<void>();
}
