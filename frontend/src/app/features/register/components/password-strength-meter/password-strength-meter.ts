import { Component, computed, input } from '@angular/core';
import { PasswordTone, passwordStrength } from '../../utils/password-strength';

const BAR_TONES: Record<PasswordTone, string> = {
  outline: 'bg-surface-variant',
  error: 'bg-error',
  tertiary: 'bg-tertiary-container',
  secondary: 'bg-secondary',
  primary: 'bg-primary',
};

const LABEL_TONES: Record<PasswordTone, string> = {
  outline: 'text-outline',
  error: 'text-error',
  tertiary: 'text-tertiary-container',
  secondary: 'text-secondary',
  primary: 'text-primary font-semibold',
};

const BAR_BASE = 'h-full w-1/4 rounded-full transition-all duration-300';

/** Four-segment strength meter driven by the password value. */
@Component({
  selector: 'app-password-strength-meter',
  template: `
    <div class="space-y-1 pt-0.5">
      <div class="flex items-center justify-between text-outline">
        <span class="text-label-sm">Seguridad de la contraseña</span>
        <span class="text-label-sm" [class]="labelClass()">{{ strength().label }}</span>
      </div>
      <div class="w-full h-1.5 bg-surface-container-low rounded-full overflow-hidden flex gap-1">
        @for (bar of bars(); track $index) {
          <div [class]="bar"></div>
        }
      </div>
    </div>
  `,
})
export class PasswordStrengthMeter {
  readonly value = input('');

  protected readonly strength = computed(() => passwordStrength(this.value()));

  protected readonly labelClass = computed(() => LABEL_TONES[this.strength().tone]);

  protected readonly bars = computed(() => {
    const filled = `${BAR_BASE} ${BAR_TONES[this.strength().tone]}`;
    const empty = `${BAR_BASE} bg-surface-variant`;
    return Array.from({ length: 4 }, (_, index) =>
      index < this.strength().score ? filled : empty,
    );
  });
}
