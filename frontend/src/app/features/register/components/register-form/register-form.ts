import { Component, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthStore } from '../../../auth/auth.store';
import { AuthNav } from '../../../auth/components/auth-nav/auth-nav';
import { GoogleSignIn } from '../../../auth/components/google-sign-in/google-sign-in';
import { ROLE_OPTIONS } from '../../models/register.model';
import { PasswordStrengthMeter } from '../password-strength-meter/password-strength-meter';
import { RegisterFormField } from '../form-field/form-field';

/**
 * Interaction panel of the register screen.
 *
 * Account creation goes through Google Identity Services against
 * POST /auth/google/register: the backend has no password support, so the
 * credential fields render disabled and the Google button is the only path.
 */
@Component({
  selector: 'app-register-form',
  imports: [RegisterFormField, PasswordStrengthMeter, GoogleSignIn, AuthNav, RouterLink],
  templateUrl: './register-form.html',
  host: {
    class:
      'lg:w-7/12 p-space-lg lg:p-space-xl flex flex-col justify-center bg-surface-container-lowest',
  },
})
export class RegisterForm {
  private readonly auth = inject(AuthStore);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected readonly roleOptions = ROLE_OPTIONS;
  protected readonly isSubmitting = this.auth.isSubmitting;
  protected readonly error = this.auth.error;

  protected onCredential(idToken: string): void {
    this.auth.registerWithGoogle(idToken).subscribe((ok) => {
      if (ok) void this.router.navigateByUrl(this.returnUrl());
    });
  }

  private returnUrl(): string {
    const requested = this.route.snapshot.queryParamMap.get('returnUrl');
    return requested && requested.startsWith('/') ? requested : '/projects';
  }
}
