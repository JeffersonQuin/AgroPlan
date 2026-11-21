export type PasswordScore = 0 | 1 | 2 | 3 | 4;

export type PasswordTone = 'outline' | 'error' | 'tertiary' | 'secondary' | 'primary';

export interface PasswordStrength {
  score: PasswordScore;
  label: string;
  tone: PasswordTone;
}

/** Four rules, one point each: length, uppercase, digit and symbol. */
export function scorePassword(value: string): PasswordScore {
  if (!value) return 0;

  let score = 0;
  if (value.length >= 8) score++;
  if (/[A-Z]/.test(value)) score++;
  if (/[0-9]/.test(value)) score++;
  if (/[^A-Za-z0-9]/.test(value)) score++;

  // A non-empty password never scores 0: it is weak, not absent.
  return Math.min(Math.max(score, 1), 4) as PasswordScore;
}

export function passwordStrength(value: string): PasswordStrength {
  if (!value) {
    return { score: 0, label: 'Mínimo 8 caracteres', tone: 'outline' };
  }

  switch (scorePassword(value)) {
    case 1:
      return { score: 1, label: 'Débil', tone: 'error' };
    case 2:
      return { score: 2, label: 'Media', tone: 'tertiary' };
    case 3:
      return { score: 3, label: 'Buena', tone: 'secondary' };
    default:
      return { score: 4, label: 'Excelente (Robusta)', tone: 'primary' };
  }
}
