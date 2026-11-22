import { Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { matAddOutline, matArrowForwardOutline } from '@ng-icons/material-symbols/outline';
import { Project } from './models/project.model';
import { ProjectsStore } from './state/projects.store';
import { AppHeader } from './components/app-header/app-header';
import { ProjectCard } from './components/project-card/project-card';
import { ProjectCreateModal } from './components/project-create-modal/project-create-modal';
import { ProjectsEmptyState } from './components/projects-empty-state/projects-empty-state';
import { ProjectsFilters } from './components/projects-filters/projects-filters';
import { ProjectsToolbar } from './components/projects-toolbar/projects-toolbar';
import { TechnicalFootnote } from './components/technical-footnote/technical-footnote';

/** Route segment of each wizard step, in order. */
const SEGMENTO_PASO: Record<number, string> = {
  1: 'terreno',
  2: 'cultivos',
  3: 'riego',
  4: 'resultado',
};

/**
 * Dashboard: the projects grid with search, status filter and sort, plus the
 * create-project dialog.
 *
 * "Nuevo proyecto" creates the project in the backend and opens step 1 for it.
 * A card resumes the step its real progress points at.
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
    NgIcon,
  ],
  viewProviders: [provideIcons({ matAddOutline, matArrowForwardOutline })],
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

  protected reintentar(): void {
    this.store.cargar();
  }

  protected toggleEmptyState(): void {
    this.emptySimulated.update((simulated) => !simulated);
  }

  /** The modal created the project: close it and open step 1. */
  protected onProjectCreated(proyectoId: string): void {
    this.closeModal();
    this.abrirPaso1(proyectoId);
  }

  /** A card asked to resume the wizard: land on the step its progress points at. */
  protected onProjectOpen(project: Project): void {
    const paso = project.nextStep.step ?? 1;
    void this.router.navigate(['/proyectos', project.id, SEGMENTO_PASO[paso] ?? 'terreno']);
  }

  private abrirPaso1(proyectoId: string): void {
    void this.router.navigate(['/proyectos', proyectoId, 'terreno']);
  }
}
