import { Component, computed, inject, signal } from '@angular/core';
import { FormField, email, form, required } from '@angular/forms/signals';
import { AuthFormModel, EMPTY_AUTH_FORM } from './auth.model';
import { AuthStore } from './auth.store';
import { LoginPasswordField } from './login-password-field';

/**
 * Credential form. Validation lives in a Signal Forms schema, so the inline
 * errors and the submit guard read from the same source of truth.
 */
@Component({
  selector: 'app-login-form',
  imports: [FormField, LoginPasswordField],
  templateUrl: './login-form.html',
})
export class LoginForm {
  private readonly store = inject(AuthStore);

  protected readonly model = signal<AuthFormModel>({ ...EMPTY_AUTH_FORM });

  protected readonly authForm = form(this.model, (path) => {
    required(path.email, { message: 'Ingresá tu correo electrónico.' });
    email(path.email, { message: 'Ingresá un correo electrónico válido.' });
    required(path.password, { message: 'Ingresá tu contraseña.' });
  });

  protected readonly isRegister = this.store.isRegister;
  protected readonly isSubmitting = this.store.isSubmitting;
  protected readonly isSuccess = this.store.isSuccess;
  protected readonly isBusy = computed(() => this.isSubmitting() || this.isSuccess());
  protected readonly submitLabel = this.store.submitLabel;

  protected readonly emailError = computed(() => {
    const state = this.authForm.email();
    return state.touched() ? (state.errors()[0]?.message ?? '') : '';
  });

  protected readonly submitIcon = computed(() => {
    if (this.isSuccess()) return 'check_circle';
    if (this.isSubmitting()) return 'progress_activity';
    return 'arrow_forward';
  });

  protected readonly statusAnnouncement = computed(() => {
    if (this.isSubmitting()) return this.store.copy().submitting;
    if (this.isSuccess()) return this.store.copy().success;
    return '';
  });

  protected async onSubmit(event: Event): Promise<void> {
    event.preventDefault();

    const emailField = this.authForm.email();
    const passwordField = this.authForm.password();
    emailField.markAsTouched();
    passwordField.markAsTouched();

    if (!emailField.valid() || !passwordField.valid()) return;

    await this.store.authenticate(this.model());
  }

  protected onDemoCredentials(): void {
    if (this.store.isRegister()) this.store.setMode('login');

    const credentials = this.store.demoCredentials();
    this.model.update((current) => ({ ...current, ...credentials }));
  }
}
