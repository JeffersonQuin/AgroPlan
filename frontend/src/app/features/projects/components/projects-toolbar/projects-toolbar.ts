import { Component, input, output } from '@angular/core';

/** Page title, active-project counter and the primary actions. */
@Component({
  selector: 'app-projects-toolbar',
  template: `
    <div
      class="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-space-md"
    >
      <div class="flex items-center gap-space-md">
        <div
          class="w-10 h-10 rounded-lg bg-surface-container-low flex items-center justify-center text-primary-container"
        >
          <span class="material-symbols-outlined text-[24px]" aria-hidden="true"
            >folder_shared</span
          >
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
          <span class="material-symbols-outlined text-[16px]" aria-hidden="true">visibility</span>
          <span>{{
            emptyStateSimulated() ? 'Ver proyectos reales' : 'Simular estado vacío'
          }}</span>
        </button>
        <button
          class="inline-flex items-center gap-space-xs bg-primary-container hover:bg-primary text-on-primary text-label-md px-space-lg py-2.5 rounded-lg transition-all shadow-sm"
          type="button"
          (click)="newProject.emit()"
        >
          <span class="material-symbols-outlined text-[18px]" aria-hidden="true">add_circle</span>
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
