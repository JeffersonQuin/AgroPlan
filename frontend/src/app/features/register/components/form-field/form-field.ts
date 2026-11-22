import { Component, computed, input } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matBadgeOutline,
  matLockOutline,
  matLockResetOutline,
  matMailOutline,
} from '@ng-icons/material-symbols/outline';
import { FieldTree, FormField } from '@angular/forms/signals';

/** Icon keys the register fields may ask for. */
export type RegisterFieldIcon = 'badge' | 'mail' | 'lock' | 'lock_reset';

/**
 * Typed map from the dynamic icon key to the imported SVG icon.
 *
 * The map is also the per-component icon registry: `provideIcons(FIELD_ICONS)`
 * registers each key, so `<ng-icon [name]="icon()" />` resolves without a
 * global registry and the tree-shaking of the icon set is preserved.
 */
const FIELD_ICONS: Record<RegisterFieldIcon, string> = {
  badge: matBadgeOutline,
  mail: matMailOutline,
  lock: matLockOutline,
  lock_reset: matLockResetOutline,
};

/**
 * Labelled text input with a leading icon, bound to a parent signal form field.
 *
 * The parent owns the form and passes the field down, so this component only
 * renders: `[formField]` wires the value, the touched state and the errors.
 * The error message is rendered by the parent's touched-only helper.
 */
@Component({
  selector: 'app-register-field',
  imports: [FormField, NgIcon],
  viewProviders: [provideIcons(FIELD_ICONS)],
  template: `
    <div class="flex flex-col gap-space-xs">
      <label class="text-label-md text-on-surface" [attr.for]="inputId()">{{ label() }}</label>
      <div class="relative flex items-center">
        <ng-icon
          class="absolute left-3 text-on-surface-variant"
          [name]="icon()"
          size="20"
          aria-hidden="true"
        />
        <input
          [id]="inputId()"
          [type]="type()"
          [formField]="field()"
          [attr.autocomplete]="autocomplete()"
          [placeholder]="placeholder()"
          class="w-full pl-10 pr-space-md py-2.5 rounded-lg bg-surface text-body-md text-on-surface placeholder:text-outline focus:bg-surface-container-lowest focus:outline-none focus:ring-2 focus:ring-primary transition-all disabled:opacity-60 disabled:cursor-not-allowed"
          [attr.aria-invalid]="invalid() ? 'true' : null"
          [attr.aria-describedby]="invalid() ? inputId() + '-error' : null"
        />
      </div>
      @if (invalid()) {
        <p [id]="inputId() + '-error'" class="text-label-sm text-error" role="alert">
          {{ error() }}
        </p>
      }
    </div>
  `,
})
export class RegisterFormField {
  /** Signal form field owned by the parent form. */
  readonly field = input.required<FieldTree<string>>();
  readonly inputId = input.required<string>();
  readonly label = input.required<string>();
  readonly icon = input<RegisterFieldIcon>('badge');
  readonly placeholder = input('');
  readonly type = input<'text' | 'email' | 'password'>('text');
  readonly autocomplete = input<string>('off');
  /** Touched-only error message computed by the parent. */
  readonly error = input('');

  protected readonly invalid = computed(() => this.error().length > 0);
}
