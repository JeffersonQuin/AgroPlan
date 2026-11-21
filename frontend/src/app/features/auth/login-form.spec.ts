import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { AuthStore } from './auth.store';
import { LoginForm } from './login-form';

describe('LoginForm', () => {
  let store: AuthStore;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [LoginForm] }).compileComponents();
    store = TestBed.inject(AuthStore);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function render() {
    const fixture = TestBed.createComponent(LoginForm);
    await fixture.whenStable();
    return fixture;
  }

  function query<T extends Element>(fixture: Awaited<ReturnType<typeof render>>, selector: string) {
    return fixture.nativeElement.querySelector(selector) as T | null;
  }

  it('shows the required error for an empty email on submit', async () => {
    const fixture = await render();

    query<HTMLFormElement>(fixture, 'form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('Ingresá tu correo electrónico.');
  });

  it('shows the invalid-format error for a malformed email', async () => {
    const fixture = await render();
    const emailInput = query<HTMLInputElement>(fixture, '#input-email')!;

    emailInput.value = 'no-es-un-correo';
    emailInput.dispatchEvent(new Event('input'));
    await fixture.whenStable();

    query<HTMLFormElement>(fixture, 'form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('Ingresá un correo electrónico válido.');
  });

  it('toggles the password visibility', async () => {
    const fixture = await render();
    const passwordInput = query<HTMLInputElement>(fixture, '#input-password')!;
    const toggle = fixture.nativeElement.querySelector(
      'app-login-password-field button[type="button"]',
    ) as HTMLButtonElement;

    expect(passwordInput.type).toBe('password');

    toggle.click();
    await fixture.whenStable();
    expect(passwordInput.type).toBe('text');

    toggle.click();
    await fixture.whenStable();
    expect(passwordInput.type).toBe('password');
  });

  it('fills the demo credentials and reveals the notice', async () => {
    const fixture = await render();
    const demoButton = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.includes('Demo Jurado'))!;

    demoButton.click();
    await fixture.whenStable();

    expect(query<HTMLInputElement>(fixture, '#input-email')!.value).toBe(
      'jurado.evaluador@agroplan.io',
    );
    expect(query<HTMLInputElement>(fixture, '#input-password')!.value).toBe('JuradoPrecision2025!');
    expect(store.demoLoaded()).toBe(true);
  });

  it('authenticates with valid credentials', async () => {
    const fixture = await render();

    const emailInput = query<HTMLInputElement>(fixture, '#input-email')!;
    emailInput.value = 'agronomo@agroplan.com';
    emailInput.dispatchEvent(new Event('input'));
    const passwordInput = query<HTMLInputElement>(fixture, '#input-password')!;
    passwordInput.value = 'Secreta123';
    passwordInput.dispatchEvent(new Event('input'));
    await fixture.whenStable();

    // Fake timers go in only after rendering: `whenStable()` needs real ones.
    vi.useFakeTimers();
    query<HTMLFormElement>(fixture, 'form')!.dispatchEvent(new Event('submit'));
    expect(store.isSubmitting()).toBe(true);

    await vi.advanceTimersByTimeAsync(1000);

    expect(store.status()).toBe('success');
  });

  it('does not authenticate when a field is empty', async () => {
    const fixture = await render();

    query<HTMLFormElement>(fixture, 'form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();

    expect(store.status()).toBe('idle');
  });
});
