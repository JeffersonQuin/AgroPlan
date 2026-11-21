import { passwordStrength, scorePassword } from '../utils/password-strength';

describe('password strength', () => {
  it('treats an empty password as absent, not weak', () => {
    expect(passwordStrength('')).toEqual({
      score: 0,
      label: 'Mínimo 8 caracteres',
      tone: 'outline',
    });
  });

  it('scores a non-empty password without any rule as weak', () => {
    expect(passwordStrength('abc')).toEqual({
      score: 1,
      label: 'Débil',
      tone: 'error',
    });
  });

  it('scores length only as weak', () => {
    expect(scorePassword('abcdefgh')).toBe(1);
    expect(passwordStrength('abcdefgh').label).toBe('Débil');
  });

  it('scores length plus uppercase as medium', () => {
    expect(scorePassword('Abcdefgh')).toBe(2);
    expect(passwordStrength('Abcdefgh')).toEqual({
      score: 2,
      label: 'Media',
      tone: 'tertiary',
    });
  });

  it('scores length, uppercase and digit as good', () => {
    expect(scorePassword('Abcdefg1')).toBe(3);
    expect(passwordStrength('Abcdefg1')).toEqual({
      score: 3,
      label: 'Buena',
      tone: 'secondary',
    });
  });

  it('scores all four rules as excellent', () => {
    expect(scorePassword('Abcdefg1!')).toBe(4);
    expect(passwordStrength('Abcdefg1!')).toEqual({
      score: 4,
      label: 'Excelente (Robusta)',
      tone: 'primary',
    });
  });

  it('counts character variety even when the password is short', () => {
    expect(scorePassword('Ab1!')).toBe(3);
  });
});
