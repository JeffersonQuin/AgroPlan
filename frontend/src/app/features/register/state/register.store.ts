import { Service, computed, signal } from '@angular/core';
import {
  RegisterFormModel,
  RegisterStatus,
  REGISTER_SUBMIT_LABELS,
} from '../models/register.model';

/** Simulated round-trip so the submit button shows a real transition. */
const REGISTER_LATENCY_MS = 900;

/**
 * Sign-up state for the register screen.
 *
 * Scope: presentation only. `register()` does NOT call the backend and creates
 * no user, token or session; it exists so the screen can be demoed end to end.
 * Wire it to the FastAPI backend before this page guards anything.
 */
@Service()
export class RegisterStore {
  private readonly _status = signal<RegisterStatus>('idle');

  readonly status = this._status.asReadonly();
  readonly isSubmitting = computed(() => this._status() === 'submitting');
  readonly isSuccess = computed(() => this._status() === 'success');
  readonly isBusy = computed(
    () => this._status() === 'submitting' || this._status() === 'success',
  );
  readonly submitLabel = computed(() => REGISTER_SUBMIT_LABELS[this._status()]);

  async register(payload: RegisterFormModel): Promise<boolean> {
    if (this._status() === 'submitting') return false;

    this._status.set('submitting');
    await new Promise((resolve) => setTimeout(resolve, REGISTER_LATENCY_MS));
    this._status.set('success');

    // Keeps the submitted payload observable for the future backend call.
    void payload;
    return true;
  }
}
