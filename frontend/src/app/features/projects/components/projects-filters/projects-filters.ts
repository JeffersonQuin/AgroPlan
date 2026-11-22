import { Component, computed, inject } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { matSearchOutline, matSortOutline } from '@ng-icons/material-symbols/outline';
import { ProjectFilter, ProjectSort } from '../../models/project.model';
import { ProjectsStore } from '../../state/projects.store';

/** Search box, status tabs and sort selector wired straight to the store. */
@Component({
  selector: 'app-projects-filters',
  imports: [NgIcon],
  viewProviders: [provideIcons({ matSearchOutline, matSortOutline })],
  template: `
    <div
      class="bg-surface-container-lowest rounded-xl p-space-md shadow-sm flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-space-md"
    >
      <div class="relative flex-1">
        <span
          class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-on-surface-variant"
        >
          <ng-icon name="matSearchOutline" size="20" aria-hidden="true" />
        </span>
        <input
          class="w-full pl-10 pr-4 py-2 bg-surface-bright rounded-lg text-body-md text-on-surface placeholder:text-on-surface-variant/70 focus:outline-none focus:bg-surface-container-lowest transition-all"
          type="search"
          id="searchInput"
          placeholder="Buscar por nombre de parcela, cultivo o sistema..."
          [value]="store.search()"
          (input)="onSearch($event)"
        />
      </div>

      <div class="flex items-center flex-wrap gap-space-sm shrink-0">
        <div class="flex flex-wrap items-center bg-surface-bright p-1 rounded-lg">
          @for (tab of tabs(); track tab.value) {
            <button
              class="px-3 py-1 rounded-md text-label-sm transition-colors"
              type="button"
              [attr.aria-pressed]="store.filter() === tab.value"
              [class]="tabClass(tab.value)"
              (click)="store.setFilter(tab.value)"
            >
              {{ tab.label }}
            </button>
          }
        </div>

        <div
          class="w-full sm:w-auto flex items-center gap-1.5 bg-surface-bright px-3 py-2 rounded-lg text-on-surface"
        >
          <ng-icon
            class="text-on-surface-variant"
            name="matSortOutline"
            size="18"
            aria-hidden="true"
          />
          <select
            class="w-full min-w-0 bg-transparent text-label-sm text-on-surface focus:outline-none cursor-pointer"
            aria-label="Ordenar proyectos"
            [value]="store.sort()"
            (change)="onSort($event)"
          >
            <option value="recent">Más recientes</option>
            <option value="area_desc">Mayor superficie</option>
            <option value="name">Alfabético (A-Z)</option>
          </select>
        </div>
      </div>
    </div>
  `,
})
export class ProjectsFilters {
  protected readonly store = inject(ProjectsStore);

  protected readonly tabs = computed(() => {
    const counts = this.store.counts();
    return [
      { value: 'all' as ProjectFilter, label: `Todos (${counts.all})` },
      { value: 'completed' as ProjectFilter, label: 'Completados' },
      { value: 'in_progress' as ProjectFilter, label: 'En curso' },
    ];
  });

  protected tabClass(filter: ProjectFilter): Record<string, boolean> {
    const active = this.store.filter() === filter;
    return {
      'bg-surface-container-lowest': active,
      'text-primary': active,
      'shadow-xs': active,
      'text-on-surface-variant': !active,
      'hover:text-on-surface': !active,
    };
  }

  protected onSearch(event: Event): void {
    this.store.setSearch((event.target as HTMLInputElement).value);
  }

  protected onSort(event: Event): void {
    this.store.setSort((event.target as HTMLSelectElement).value as ProjectSort);
  }
}
