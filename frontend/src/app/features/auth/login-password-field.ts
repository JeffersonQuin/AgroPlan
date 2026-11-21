import { Component, computed, input, signal } from '@angular/core';
import { FieldTree, FormField } from '@angular/forms/signals';

/**
 * Password input with a visibility toggle and inline validation message.
 * Login-specific: it carries the "forgot password" affordance of the screen.
 */
@Component({
  selector: 'app-login-password-field',
  imports: [FormField],
  template: `
    <div class="flex flex-col gap-space-xs">
      <div class="flex items-center justify-between">
        <label class="text-label-md text-on-surface" [attr.for]="inputId()">
          {{ label() }}
        </label>
        <a
          class="text-label-sm text-primary hover:text-secondary underline decoration-dotted transition-colors"
          href="#"
        >
          ¿Olvidaste tu contraseña?
        </a>
      </div>

      <div class="relative flex items-center">
        <span
          class="material-symbols-outlined absolute left-3 text-on-surface-variant text-[18px]"
          aria-hidden="true"
          >lock</span
        >
        <input
          [id]="inputId()"
          [type]="visible() ? 'text' : 'password'"
          [formField]="field()"
          [attr.aria-invalid]="hasError()"
          [attr.aria-describedby]="hasError() ? inputId() + '-error' : null"
          class="w-full pl-10 pr-11 py-2.5 rounded-lg bg-surface text-body-md text-on-surface placeholder:text-outline focus:bg-surface-container-lowest focus:outline-none focus:ring-2 focus:ring-primary transition-all"
          placeholder="••••••••••••"
          autocomplete="current-password"
        />
        <button
          class="absolute right-3 text-on-surface-variant hover:text-on-surface p-1 rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-primary transition-colors"
          type="button"
          [attr.aria-label]="visible() ? 'Ocultar contraseña' : 'Mostrar contraseña'"
          [attr.aria-pressed]="visible()"
          (click)="visible.set(!visible())"
        >
          <span class="material-symbols-outlined text-[18px]" aria-hidden="true">{{
            visible() ? 'visibility_off' : 'visibility'
          }}</span>
        </button>
      </div>

      @if (hasError()) {
        <p [id]="inputId() + '-error'" class="text-label-sm text-error" role="alert">
          {{ errorMessage() }}
        </p>
      }
    </div>
  `,
})
export class LoginPasswordField {
  readonly field = input.required<FieldTree<string>>();
  readonly inputId = input.required<string>();
  readonly label = input('Contraseña');

  protected readonly visible = signal(false);

  protected readonly errorMessage = computed(() => {
    const state = this.field()();
    return state.touched() ? (state.errors()[0]?.message ?? '') : '';
  });

  protected readonly hasError = computed(() => this.errorMessage().length > 0);
}
