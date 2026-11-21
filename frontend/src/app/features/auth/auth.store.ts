import { Service, computed, signal } from '@angular/core';
import {
  AUTH_COPY,
  AuthFormModel,
  AuthMode,
  AuthStatus,
  DEMO_CREDENTIALS,
} from './auth.model';

/** Simulated round-trip so the submit button shows a real transition. */
const AUTH_LATENCY_MS = 900;

/**
 * Holds the state shared by the login hero, the mode tabs and the form.
 *
 * Scope: presentation only. `authenticate()` does NOT call the backend and
 * creates no token, cookie or session; it exists so the screen can be demoed
 * end to end. Wire it to the FastAPI backend before this page guards anything.
 */
@Service()
export class AuthStore {
  private readonly _mode = signal<AuthMode>('login');
  private readonly _status = signal<AuthStatus>('idle');
  private readonly _demoLoaded = signal(false);

  readonly mode = this._mode.asReadonly();
  readonly status = this._status.asReadonly();
  readonly demoLoaded = this._demoLoaded.asReadonly();

  readonly isRegister = computed(() => this._mode() === 'register');
  readonly isSubmitting = computed(() => this._status() === 'submitting');
  readonly isSuccess = computed(() => this._status() === 'success');
  readonly copy = computed(() => AUTH_COPY[this._mode()]);
  readonly submitLabel = computed(() => {
    const status = this._status();
    if (status === 'submitting') return this.copy().submitting;
    if (status === 'success') return this.copy().success;
    return this.copy().submit;
  });

  setMode(mode: AuthMode): void {
    if (this._mode() === mode) return;
    this._mode.set(mode);
    this._status.set('idle');
    this._demoLoaded.set(false);
  }

  /** Fills the form with the jury demo credentials and reveals the notice. */
  demoCredentials(): { email: string; password: string } {
    this._demoLoaded.set(true);
    return { ...DEMO_CREDENTIALS };
  }

  async authenticate(credentials: AuthFormModel): Promise<boolean> {
    if (this._status() === 'submitting') return false;

    this._status.set('submitting');
    await new Promise((resolve) => setTimeout(resolve, AUTH_LATENCY_MS));
    this._status.set('success');

    // Keeps the submitted payload observable for the future backend call.
    void credentials;
    return true;
  }
}
