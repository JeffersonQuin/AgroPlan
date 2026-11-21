import { Component, input } from '@angular/core';

/**
 * Labelled text input with a leading icon.
 *
 * The register screen only signs in with Google, so these fields are
 * presentational: the backend has no password support yet and they render
 * disabled until it does.
 */
@Component({
  selector: 'app-register-field',
  template: `
    <div class="space-y-1">
      <label class="block text-label-md text-on-surface" [attr.for]="inputId()">
        {{ label() }}
      </label>
      <div class="relative rounded-lg bg-surface-container-low">
        <span
          class="material-symbols-outlined absolute left-3 top-2.5 text-outline text-[20px]"
          aria-hidden="true"
          >{{ icon() }}</span
        >
        <input
          [id]="inputId()"
          [type]="type()"
          [attr.autocomplete]="autocomplete()"
          class="w-full bg-transparent py-2.5 pl-10 pr-space-md text-on-surface text-body-md placeholder:text-outline focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
          [placeholder]="placeholder()"
          [attr.aria-label]="label()"
          disabled
        />
      </div>
    </div>
  `,
})
export class RegisterFormField {
  readonly inputId = input.required<string>();
  readonly label = input.required<string>();
  readonly icon = input('edit');
  readonly placeholder = input('');
  readonly type = input<'text' | 'email' | 'password'>('text');
  readonly autocomplete = input<string>('off');
}
