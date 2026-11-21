import { Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';

type AuthScreen = 'login' | 'register';

interface NavItem {
  screen: AuthScreen;
  label: string;
  path: string;
}

const ITEMS: readonly NavItem[] = [
  { screen: 'login', label: 'Iniciar Sesión', path: '/login' },
  { screen: 'register', label: 'Crear Cuenta', path: '/register' },
];

/**
 * Shared "Iniciar Sesión / Crear Cuenta" switch.
 *
 * Both screens render the same component so the way back is always in the same
 * place: the register panel is long, and a footer-only link disappears below
 * the fold.
 */
@Component({
  selector: 'app-auth-nav',
  imports: [RouterLink],
  template: `
    <nav class="inline-flex p-0.5 rounded-lg bg-surface-container-low" aria-label="Acceso">
      @for (item of items(); track item.screen) {
        @if (item.active) {
          <span
            class="px-space-md py-1 rounded-md text-label-sm bg-surface-container-lowest text-primary shadow-sm"
            aria-current="page"
            >{{ item.label }}</span
          >
        } @else {
          <a
            class="px-space-md py-1 rounded-md text-label-sm text-on-surface-variant hover:text-on-surface transition-colors"
            [routerLink]="item.path"
            >{{ item.label }}</a
          >
        }
      }
    </nav>
  `,
})
export class AuthNav {
  readonly active = input.required<AuthScreen>();

  protected readonly items = computed(() =>
    ITEMS.map((item) => ({ ...item, active: item.screen === this.active() })),
  );
}
