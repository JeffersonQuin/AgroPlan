import { Component, input, signal } from '@angular/core';

/**
 * Password input with a visibility toggle.
 *
 * Login-specific: it carries the "forgot password" affordance of the screen.
 * It is disabled while the backend does not accept credentials.
 */
@Component({
  selector: 'app-login-password-field',
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
          [disabled]="disabled()"
          class="w-full pl-10 pr-11 py-2.5 rounded-lg bg-surface text-body-md text-on-surface placeholder:text-outline focus:bg-surface-container-lowest focus:outline-none focus:ring-2 focus:ring-primary transition-all disabled:opacity-60 disabled:cursor-not-allowed"
          placeholder="••••••••••••"
          autocomplete="current-password"
        />
        <button
          class="absolute right-3 text-on-surface-variant hover:text-on-surface p-1 rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          type="button"
          [disabled]="disabled()"
          [attr.aria-label]="visible() ? 'Ocultar contraseña' : 'Mostrar contraseña'"
          [attr.aria-pressed]="visible()"
          (click)="visible.set(!visible())"
        >
          <span class="material-symbols-outlined text-[18px]" aria-hidden="true">{{
            visible() ? 'visibility_off' : 'visibility'
          }}</span>
        </button>
      </div>
    </div>
  `,
})
export class LoginPasswordField {
  readonly inputId = input.required<string>();
  readonly label = input('Contraseña');
  readonly disabled = input(false);

  protected readonly visible = signal(false);
}
