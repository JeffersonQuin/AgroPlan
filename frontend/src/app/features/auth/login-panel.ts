import { Component, inject } from '@angular/core';
import { AuthNav } from './components/auth-nav/auth-nav';
import { AuthStore } from './auth.store';
import { LoginForm } from './login-form';

/**
 * Interaction panel: brand bar, entry navigation, heading, Google sign-in and
 * the trust footer.
 *
 * "Crear Cuenta" navigates to the dedicated register screen instead of
 * switching a local mode: the register screen is a different layout with its
 * own hero, and it hits the register endpoint.
 */
@Component({
  selector: 'app-login-panel',
  imports: [LoginForm, AuthNav],
  templateUrl: './login-panel.html',
  host: {
    class:
      'w-full lg:w-7/12 p-space-lg lg:p-margin-desktop bg-surface-container-lowest flex flex-col justify-between',
  },
})
export class LoginPanel {
  protected readonly store = inject(AuthStore);
  protected readonly copy = this.store.copy;
}
