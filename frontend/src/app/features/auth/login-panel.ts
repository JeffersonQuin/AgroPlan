import { Component, computed, inject } from '@angular/core';
import { AuthMode } from './auth.model';
import { AuthStore } from './auth.store';
import { LoginForm } from './login-form';

/**
 * Interaction panel: brand bar, login/register tabs, heading, form,
 * demo notice and the trust footer.
 */
@Component({
  selector: 'app-login-panel',
  imports: [LoginForm],
  templateUrl: './login-panel.html',
  host: {
    class:
      'w-full lg:w-7/12 p-space-lg lg:p-margin-desktop bg-surface-container-lowest flex flex-col justify-between',
  },
})
export class LoginPanel {
  private readonly store = inject(AuthStore);

  protected readonly copy = this.store.copy;
  protected readonly mode = this.store.mode;

  protected readonly loginTabClass = computed(() => this.tabClass('login'));
  protected readonly registerTabClass = computed(() => this.tabClass('register'));

  private tabClass(mode: AuthMode): Record<string, boolean> {
    const active = this.mode() === mode;
    return {
      'bg-surface-container-lowest': active,
      'text-primary': active,
      'shadow-sm': active,
      'text-on-surface-variant': !active,
      'hover:text-on-surface': !active,
    };
  }

  protected setMode(mode: AuthMode): void {
    this.store.setMode(mode);
  }
}
