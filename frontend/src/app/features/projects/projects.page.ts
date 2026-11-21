import { Component, computed, inject, signal } from '@angular/core';
import { ProjectsStore } from './state/projects.store';
import { AppHeader } from './components/app-header/app-header';
import { ProjectCard } from './components/project-card/project-card';
import { ProjectCreateModal } from './components/project-create-modal/project-create-modal';
import { ProjectsEmptyState } from './components/projects-empty-state/projects-empty-state';
import { ProjectsFilters } from './components/projects-filters/projects-filters';
import { ProjectsToolbar } from './components/projects-toolbar/projects-toolbar';
import { TechnicalFootnote } from './components/technical-footnote/technical-footnote';

/**
 * Dashboard: the projects grid with search, status filter and sort, plus the
 * create-project dialog.
 *
 * The wizard hand-off ("Abrir proyecto" / "Continuar") is not wired yet: the
 * Terreno step does not exist, so the card actions only emit their event.
 */
@Component({
  selector: 'app-projects-page',
  imports: [
    AppHeader,
    ProjectsToolbar,
    ProjectsFilters,
    ProjectCard,
    ProjectsEmptyState,
    TechnicalFootnote,
    ProjectCreateModal,
  ],
  templateUrl: './projects.page.html',
})
export class ProjectsPage {
  protected readonly store = inject(ProjectsStore);

  protected readonly modalOpen = signal(false);
  protected readonly emptySimulated = signal(false);

  protected readonly showOnboarding = computed(
    () => this.emptySimulated() || this.store.projects().length === 0,
  );

  protected readonly showNoResults = computed(
    () => !this.showOnboarding() && this.store.visibleProjects().length === 0,
  );

  protected openModal(): void {
    this.modalOpen.set(true);
  }

  protected closeModal(): void {
    this.modalOpen.set(false);
  }

  protected toggleEmptyState(): void {
    this.emptySimulated.update((simulated) => !simulated);
  }
}
