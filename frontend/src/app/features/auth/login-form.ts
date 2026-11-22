import { Component, computed, inject, signal } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matAlternateEmailOutline,
  matCloudDoneOutline,
  matLockOutline,
  matProgressActivityOutline,
  matVisibilityOffOutline,
  matVisibilityOutline,
} from '@ng-icons/material-symbols/outline';
import { FormField, email as emailFormat, form, required } from '@angular/forms/signals';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthStore } from './auth.store';
import { GoogleSignIn } from './components/google-sign-in/google-sign-in';

interface LoginModel {
  email: string;
  password: string;
  rememberStation: boolean;
}

/**
 * Interaction panel of the auth screen.
 *
 * Google stays the primary path: its button renders first and is never gated.
 * Email + password is the fallback (`POST /auth/login`, see `auth.model.ts`) and
 * is validated on the client only for presence, so an account created before a
 * password policy existed can still sign in.
 */
@Component({
  selector: 'app-login-form',
  imports: [GoogleSignIn, FormField, NgIcon],
  templateUrl: './login-form.html',
  viewProviders: [
    provideIcons({
      matAlternateEmailOutline,
      matCloudDoneOutline,
      matLockOutline,
      matProgressActivityOutline,
      matVisibilityOffOutline,
      matVisibilityOutline,
    }),
  ],
})
export class LoginForm {
  protected readonly store = inject(AuthStore);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected readonly isSubmitting = this.store.isSubmitting;
  protected readonly error = this.store.error;
  protected readonly copy = this.store.copy;

  protected readonly model = signal<LoginModel>({
    email: '',
    password: '',
    rememberStation: readRememberStation(),
  });

  protected readonly form = form(this.model, (path) => {
    required(path.email, { message: 'Ingresá tu correo profesional.' });
    emailFormat(path.email, { message: 'Ese correo no parece válido.' });
    required(path.password, { message: 'Ingresá tu contraseña.' });
  });

  protected readonly emailError = computed(() => errorOf(this.form.email()));
  protected readonly passwordError = computed(() => errorOf(this.form.password()));

  protected readonly passwordVisible = signal(false);

  protected togglePassword(): void {
    this.passwordVisible.update((visible) => !visible);
  }

  protected onCredential(idToken: string): void {
    this.store.loginWithGoogle(idToken).subscribe((ok) => {
      if (ok) void this.router.navigateByUrl(this.returnUrl());
    });
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    if (this.isSubmitting()) return;

    const email = this.form.email();
    const password = this.form.password();
    email.markAsTouched();
    password.markAsTouched();
    if (!email.valid() || !password.valid()) return;

    const { rememberStation } = this.model();
    this.store
      .loginWithPassword({ email: this.model().email.trim(), password: this.model().password })
      .subscribe((ok) => {
        if (!ok) return;
        if (rememberStation) this.rememberStation();
        void this.router.navigateByUrl(this.returnUrl());
      });
  }

  /** Marks the workstation as trusted for the session (UI preference only). */
  private rememberStation(): void {
    try {
      sessionStorage.setItem(REMEMBER_STATION_KEY, '1');
    } catch {
      // Private mode blocks storage: the preference is cosmetic, so ignore it.
    }
  }

  private returnUrl(): string {
    const requested = this.route.snapshot.queryParamMap.get('returnUrl');
    return requested && requested.startsWith('/') ? requested : '/projects';
  }
}

/** Touched-only error message of a signal form field. */
function errorOf(field: { touched: () => boolean; errors: () => { message?: string }[] }): string {
  return field.touched() ? (field.errors()[0]?.message ?? '') : '';
}

const REMEMBER_STATION_KEY = 'agroplan.rememberStation';

/** UI preference only: it remembers the checkbox, it does not change token storage. */
function readRememberStation(): boolean {
  try {
    return sessionStorage.getItem(REMEMBER_STATION_KEY) === '1';
  } catch {
    return true;
  }
}
