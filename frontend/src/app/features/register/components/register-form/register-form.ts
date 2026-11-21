import { Component, computed, inject, signal } from '@angular/core';
import { FormField, email, form, minLength, required } from '@angular/forms/signals';
import { RouterLink } from '@angular/router';
import {
  EMPTY_REGISTER_FORM,
  RegisterFormModel,
  REGISTER_MIN_PASSWORD_LENGTH,
  ROLE_OPTIONS,
} from '../../models/register.model';
import { RegisterStore } from '../../state/register.store';
import { RegisterFormField } from '../form-field/form-field';
import { PasswordStrengthMeter } from '../password-strength-meter/password-strength-meter';

/**
 * Interaction panel of the register screen: brand bar, heading, social entry
 * point, the sign-up form and the switch-to-login footer.
 *
 * Validation lives in a Signal Forms schema, so inline errors and the submit
 * guard read from the same source of truth.
 */
@Component({
  selector: 'app-register-form',
  imports: [FormField, RegisterFormField, PasswordStrengthMeter, RouterLink],
  templateUrl: './register-form.html',
  host: {
    class:
      'lg:w-7/12 p-space-lg lg:p-space-xl flex flex-col justify-center bg-surface-container-lowest',
  },
})
export class RegisterForm {
  private readonly store = inject(RegisterStore);

  protected readonly model = signal<RegisterFormModel>({ ...EMPTY_REGISTER_FORM });

  protected readonly registerForm = form(this.model, (path) => {
    required(path.fullName, { message: 'Ingresá tu nombre completo.' });
    required(path.workEmail, { message: 'Ingresá tu correo profesional.' });
    email(path.workEmail, { message: 'Ingresá un correo electrónico válido.' });
    required(path.userRole, { message: 'Elegí tu rol o especialidad agronómica.' });
    required(path.password, { message: 'Ingresá una contraseña.' });
    minLength(path.password, REGISTER_MIN_PASSWORD_LENGTH, {
      message: `La contraseña debe tener al menos ${REGISTER_MIN_PASSWORD_LENGTH} caracteres.`,
    });
    required(path.confirmPassword, { message: 'Repetí la contraseña.' });
  });

  protected readonly roleOptions = ROLE_OPTIONS;

  protected readonly isBusy = this.store.isBusy;
  protected readonly isSubmitting = this.store.isSubmitting;
  protected readonly submitLabel = this.store.submitLabel;

  protected readonly password = computed(() => this.model().password);

  protected readonly passwordMismatch = computed(() => {
    const { password, confirmPassword } = this.model();
    return confirmPassword.length > 0 && password !== confirmPassword;
  });

  protected readonly roleError = computed(() => {
    const state = this.registerForm.userRole();
    return state.touched() ? (state.errors()[0]?.message ?? '') : '';
  });

  protected readonly submitIcon = computed(() => {
    if (this.store.isSuccess()) return 'check_circle';
    if (this.isSubmitting()) return 'progress_activity';
    return 'how_to_reg';
  });

  protected readonly statusAnnouncement = computed(() => {
    if (this.isSubmitting()) return this.store.submitLabel();
    if (this.store.isSuccess()) return 'Cuenta creada.';
    return '';
  });

  protected readonly termsError = signal(false);

  protected async onSubmit(event: Event): Promise<void> {
    event.preventDefault();

    const fields = [
      this.registerForm.fullName(),
      this.registerForm.workEmail(),
      this.registerForm.userRole(),
      this.registerForm.password(),
      this.registerForm.confirmPassword(),
    ];
    fields.forEach((field) => field.markAsTouched());

    this.termsError.set(!this.model().termsAccepted);
    if (this.termsError()) return;
    if (this.passwordMismatch()) return;
    if (!fields.every((field) => field.valid())) return;

    await this.store.register(this.model());
  }
}
