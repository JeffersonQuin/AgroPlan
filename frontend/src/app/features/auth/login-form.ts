import { Component, computed, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthStore } from './auth.store';
import { GoogleSignIn } from './components/google-sign-in/google-sign-in';
import { LoginPasswordField } from './login-password-field';

/**
 * Interaction panel of the auth screen.
 *
 * Sign-in goes through Google Identity Services: the backend only accepts a
 * Google ID token (POST /auth/google). The credential fields of the mockup stay
 * visible but disabled until the backend supports passwords.
 */
@Component({
  selector: 'app-login-form',
  imports: [GoogleSignIn, LoginPasswordField],
  templateUrl: './login-form.html',
})
export class LoginForm {
  protected readonly store = inject(AuthStore);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected readonly isRegister = this.store.isRegister;
  protected readonly isSubmitting = this.store.isSubmitting;
  protected readonly error = this.store.error;
  protected readonly emailHint = computed(() =>
    this.isRegister() ? 'Se usará el correo de tu cuenta de Google.' : '',
  );

  protected onCredential(idToken: string): void {
    this.store.loginWithGoogle(idToken).subscribe((ok) => {
      if (ok) void this.router.navigateByUrl(this.returnUrl());
    });
  }

  private returnUrl(): string {
    const requested = this.route.snapshot.queryParamMap.get('returnUrl');
    return requested && requested.startsWith('/') ? requested : '/projects';
  }
}
