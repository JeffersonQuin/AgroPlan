import { Component, computed, input } from '@angular/core';
import { FieldTree, FormField } from '@angular/forms/signals';

/**
 * Labelled text input with a leading icon and inline validation message.
 * Feature-scoped to the register screen; wraps the `[formField]` binding so the
 * form template stays declarative.
 */
@Component({
  selector: 'app-register-field',
  imports: [FormField],
  template: `
    <div class="space-y-1">
      <label class="block text-label-md text-on-surface" [attr.for]="inputId()">
        {{ label() }}
      </label>
      <div
        class="relative rounded-lg bg-surface-container-low focus-within:bg-surface-bright focus-within:ring-2 focus-within:ring-primary"
      >
        <span
          class="material-symbols-outlined absolute left-3 top-2.5 text-outline text-[20px]"
          aria-hidden="true"
          >{{ icon() }}</span
        >
        <input
          [id]="inputId()"
          [type]="type()"
          [formField]="field()"
          [attr.aria-invalid]="hasError()"
          [attr.aria-describedby]="hasError() ? inputId() + '-error' : null"
          [attr.autocomplete]="autocomplete()"
          class="w-full bg-transparent py-2.5 pl-10 pr-space-md text-on-surface text-body-md placeholder:text-outline focus:outline-none"
          [placeholder]="placeholder()"
          [attr.aria-label]="label()"
        />
      </div>
      @if (hasError()) {
        <p [id]="inputId() + '-error'" class="text-label-sm text-error" role="alert">
          {{ errorMessage() }}
        </p>
      }
    </div>
  `,
})
export class RegisterFormField {
  readonly field = input.required<FieldTree<string>>();
  readonly inputId = input.required<string>();
  readonly label = input.required<string>();
  readonly icon = input('edit');
  readonly placeholder = input('');
  readonly type = input<'text' | 'email' | 'password'>('text');
  readonly autocomplete = input<string>('off');

  protected readonly errorMessage = computed(() => {
    const state = this.field()();
    return state.touched() ? (state.errors()[0]?.message ?? '') : '';
  });

  protected readonly hasError = computed(() => this.errorMessage().length > 0);
}
