import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { EMPTY_AUTH_FORM } from './auth.model';
import { AuthStore } from './auth.store';

describe('AuthStore', () => {
  let store: AuthStore;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    store = TestBed.inject(AuthStore);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts in login mode and idle', () => {
    expect(store.mode()).toBe('login');
    expect(store.isRegister()).toBe(false);
    expect(store.status()).toBe('idle');
    expect(store.submitLabel()).toBe('Iniciar Sesión en AgroPlan');
  });

  it('swaps the copy when switching to register mode', () => {
    store.setMode('register');

    expect(store.isRegister()).toBe(true);
    expect(store.copy().title).toBe('Crea tu cuenta técnica');
    expect(store.submitLabel()).toBe('Registrarse y Crear Espacio');
  });

  it('clears the submit status and the demo notice when switching mode', async () => {
    vi.useFakeTimers();
    const pending = store.authenticate(EMPTY_AUTH_FORM);
    await vi.advanceTimersByTimeAsync(1000);
    await pending;
    expect(store.status()).toBe('success');

    store.demoCredentials();
    expect(store.demoLoaded()).toBe(true);

    store.setMode('register');
    expect(store.status()).toBe('idle');
    expect(store.demoLoaded()).toBe(false);
  });

  it('reports the submitting and success labels while authenticating', async () => {
    vi.useFakeTimers();

    const pending = store.authenticate(EMPTY_AUTH_FORM);
    expect(store.isSubmitting()).toBe(true);
    expect(store.submitLabel()).toBe('Verificando estación…');

    await vi.advanceTimersByTimeAsync(1000);
    await pending;

    expect(store.isSuccess()).toBe(true);
    expect(store.submitLabel()).toBe('Acceso Autorizado');
  });

  it('rejects a second submit while one is still in flight', async () => {
    vi.useFakeTimers();

    const first = store.authenticate(EMPTY_AUTH_FORM);
    const second = await store.authenticate(EMPTY_AUTH_FORM);
    expect(second).toBe(false);

    await vi.advanceTimersByTimeAsync(1000);
    await first;
  });

  it('returns the demo credentials', () => {
    expect(store.demoCredentials()).toEqual({
      email: 'jurado.evaluador@agroplan.io',
      password: 'JuradoPrecision2025!',
    });
  });
});
