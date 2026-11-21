import { Component, computed, inject, output, signal } from '@angular/core';
import { FormField, form, maxLength, required } from '@angular/forms/signals';
import { CreateProjectInput, UnitSystem } from '../../models/project.model';
import { ProjectsStore } from '../../state/projects.store';

const NAME_MAX_LENGTH = 60;

/**
 * "+ Nuevo proyecto" dialog. Collects the identity of the project and creates
 * it in the store; the wizard hand-off lands when the Terreno step exists.
 */
@Component({
  selector: 'app-project-create-modal',
  imports: [FormField],
  templateUrl: './project-create-modal.html',
  host: {
    class: 'fixed inset-0 z-50 flex items-center justify-center p-4',
    '(document:keydown.escape)': 'close.emit()',
  },
})
export class ProjectCreateModal {
  private readonly store = inject(ProjectsStore);

  readonly close = output<void>();

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

    const name = this.form.name();
    name.markAsTouched();
    if (!name.valid()) return;

    this.store.create(this.model());
    this.close.emit();
  }
}
