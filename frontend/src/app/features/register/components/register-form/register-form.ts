import { Component, computed, inject, signal } from '@angular/core';
import {
  FormField,
  email as emailFormat,
  form,
  minLength,
  required,
  validate,
} from '@angular/forms/signals';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matAgricultureOutline,
  matArrowForwardOutline,
  matEngineeringOutline,
  matKeyboardArrowDownOutline,
} from '@ng-icons/material-symbols/outline';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthStore } from '../../../auth/auth.store';
import { AuthNav } from '../../../auth/components/auth-nav/auth-nav';
import { GoogleSignIn } from '../../../auth/components/google-sign-in/google-sign-in';
import { ROLE_OPTIONS } from '../../models/register.model';
import { PasswordStrengthMeter } from '../password-strength-meter/password-strength-meter';
import { RegisterFormField } from '../form-field/form-field';

interface RegisterModel {
  nombre: string;
  email: string;
  rol: string;
  password: string;
  confirmPassword: string;
  terms: boolean;
}

const PASSWORD_MIN_LENGTH = 8;

/**
 * Interaction panel of the register screen.
 *
 * Google stays the primary path: its button renders first and is never gated.
 * Email + password is the fallback and speaks `POST /auth/register` (see
 * `auth.model.ts`); it is validated on the client for presence, format, length,
 * confirmation and terms.
 */
@Component({
  selector: 'app-register-form',
  imports: [
    RegisterFormField,
    PasswordStrengthMeter,
    GoogleSignIn,
    AuthNav,
    RouterLink,
    NgIcon,
    FormField,
  ],
  templateUrl: './register-form.html',
  viewProviders: [
    provideIcons({
      matAgricultureOutline,
      matArrowForwardOutline,
      matEngineeringOutline,
      matKeyboardArrowDownOutline,
    }),
  ],
  host: {
    class:
      'w-full lg:w-7/12 p-space-md sm:p-space-lg lg:p-space-xl flex flex-col justify-center bg-surface-container-lowest',
  },
})
export class RegisterForm {
  private readonly store = inject(AuthStore);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected readonly roleOptions = ROLE_OPTIONS;
  protected readonly isSubmitting = this.store.isSubmitting;
  protected readonly error = this.store.error;

  protected readonly model = signal<RegisterModel>({
    nombre: '',
    email: '',
    rol: '',
    password: '',
    confirmPassword: '',
    terms: false,
  });

  protected readonly form = form(this.model, (path) => {
    required(path.nombre, { message: 'Ingresá tu nombre completo.' });
    required(path.email, { message: 'Ingresá tu correo profesional.' });
    emailFormat(path.email, { message: 'Ese correo no parece válido.' });
    required(path.rol, { message: 'Seleccioná tu rol o especialidad.' });
    required(path.password, { message: 'Ingresá una contraseña.' });
    minLength(path.password, PASSWORD_MIN_LENGTH, {
      message: `La contraseña necesita al menos ${PASSWORD_MIN_LENGTH} caracteres.`,
    });
    required(path.confirmPassword, { message: 'Repetí tu contraseña.' });
    validate(path.confirmPassword, ({ value, valueOf }) => {
      const confirmation = value();
      if (confirmation.length === 0) return undefined;
      return confirmation === valueOf(path.password)
        ? undefined
        : { kind: 'passwordMismatch', message: 'Las contraseñas no coinciden.' };
    });
    validate(path.terms, ({ value }) =>
      value()
        ? undefined
        : {
            kind: 'termsRequired',
            message: 'Tenés que aceptar los términos para crear tu cuenta.',
          },
    );
  });

  protected readonly nombreError = computed(() => errorOf(this.form.nombre()));
  protected readonly emailError = computed(() => errorOf(this.form.email()));
  protected readonly rolError = computed(() => errorOf(this.form.rol()));
  protected readonly passwordError = computed(() => errorOf(this.form.password()));
  protected readonly confirmPasswordError = computed(() => errorOf(this.form.confirmPassword()));
  protected readonly termsError = computed(() => errorOf(this.form.terms()));

  /** Typed password value for the strength meter. */
  protected readonly password = computed(() => this.model().password);

  protected onCredential(idToken: string): void {
    this.store.registerWithGoogle(idToken).subscribe((ok) => {
      if (ok) void this.router.navigateByUrl(this.returnUrl());
    });
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    if (this.isSubmitting()) return;

    for (const field of [
      this.form.nombre(),
      this.form.email(),
      this.form.rol(),
      this.form.password(),
      this.form.confirmPassword(),
      this.form.terms(),
    ]) {
      field.markAsTouched();
    }

    if (
      !this.form.nombre().valid() ||
      !this.form.email().valid() ||
      !this.form.rol().valid() ||
      !this.form.password().valid() ||
      !this.form.confirmPassword().valid() ||
      !this.form.terms().valid()
    ) {
      return;
    }

    const { nombre, email, password, rol } = this.model();
    this.store
      .registerWithPassword({ nombre: nombre.trim(), email: email.trim(), password, rol })
      .subscribe((ok) => {
        if (ok) void this.router.navigateByUrl(this.returnUrl());
      });
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
