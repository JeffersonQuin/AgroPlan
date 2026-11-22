import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, output, signal } from '@angular/core';
import { FormField, form, maxLength, required } from '@angular/forms/signals';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matAddLocationAltOutline,
  matArrowForwardOutline,
  matCloseOutline,
  matLightbulbOutline,
  matLocationOnOutline,
} from '@ng-icons/material-symbols/outline';
import { CreateProjectInput, UnitSystem } from '../../models/project.model';
import { ProjectsStore, mensajeDeError } from '../../state/projects.store';

const NAME_MAX_LENGTH = 60;

/**
 * "+ Nuevo proyecto" dialog. Collects the identity of the project, creates it in
 * the backend and hands the real id back to the page, which navigates to step 1.
 */
@Component({
  selector: 'app-project-create-modal',
  imports: [FormField, NgIcon],
  viewProviders: [
    provideIcons({
      matAddLocationAltOutline,
      matArrowForwardOutline,
      matCloseOutline,
      matLightbulbOutline,
      matLocationOnOutline,
    }),
  ],
  templateUrl: './project-create-modal.html',
  host: {
    class: 'fixed inset-0 z-50 flex items-start sm:items-center justify-center overflow-y-auto p-4',
    '(document:keydown.escape)': 'close.emit()',
  },
})
export class ProjectCreateModal {
  private readonly store = inject(ProjectsStore);

  readonly close = output<void>();
  /** Emitted with the new project id once the backend accepted it. */
  readonly created = output<string>();

  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly model = signal<CreateProjectInput>({
    name: '',
    location: '',
    unitSystem: 'metric',
  });

  protected readonly form = form(this.model, (path) => {
    required(path.name, { message: 'Poné un nombre para el proyecto.' });
    maxLength(path.name, NAME_MAX_LENGTH, {
      message: `El nombre no puede superar los ${NAME_MAX_LENGTH} caracteres.`,
    });
  });

  protected readonly nameMaxLength = NAME_MAX_LENGTH;
  protected readonly nameLength = computed(() => this.model().name.length);
  protected readonly unitSystem = computed(() => this.model().unitSystem);

  protected readonly nameError = computed(() => {
    const state = this.form.name();
    return state.touched() ? (state.errors()[0]?.message ?? '') : '';
  });

  protected setUnitSystem(unitSystem: UnitSystem): void {
    this.model.update((current) => ({ ...current, unitSystem }));
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    if (this.submitting()) return;

    const name = this.form.name();
    name.markAsTouched();
    if (!name.valid()) return;

    this.submitting.set(true);
    this.error.set(null);
    this.store.crear(this.model()).subscribe({
      next: (proyecto) => {
        this.submitting.set(false);
        this.created.emit(proyecto.id);
      },
      error: (error: HttpErrorResponse) => {
        this.submitting.set(false);
        this.error.set(mensajeDeError(error));
      },
    });
  }
}
