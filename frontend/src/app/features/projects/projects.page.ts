import { Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
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
 * "Nuevo proyecto" creates the project in the backend and opens step 1 for it.
 * Opening an existing project from a card is still pending: the wizard resume
 * needs the step-2..4 screens.
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
  private readonly router = inject(Router);

  protected readonly modalOpen = signal(false);
  protected readonly emptySimulated = signal(false);

  protected readonly showOnboarding = computed(
    () => this.emptySimulated() || this.store.projects().length === 0,
  );

  constructor() {
    this.store.cargar();
  }


  protected openModal(): void {
    this.modalOpen.set(true);
  }

  protected closeModal(): void {
    this.modalOpen.set(false);
  }

  protected toggleEmptyState(): void {
    this.emptySimulated.update((simulated) => !simulated);
  }

  /** The modal created the project: close it and open step 1. */
  protected onProjectCreated(proyectoId: string): void {
    this.closeModal();
    void this.router.navigate(['/proyectos', proyectoId, 'terreno']);
  }
}
