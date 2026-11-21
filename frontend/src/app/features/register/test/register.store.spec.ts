import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { EMPTY_REGISTER_FORM } from '../models/register.model';
import { RegisterStore } from '../state/register.store';

describe('RegisterStore', () => {
  let store: RegisterStore;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    store = TestBed.inject(RegisterStore);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts idle with the default submit label', () => {
    expect(store.status()).toBe('idle');
    expect(store.submitLabel()).toBe('Crear Cuenta y Empezar');
    expect(store.isBusy()).toBe(false);
  });

  it('walks through submitting to success', async () => {
    vi.useFakeTimers();

    const pending = store.register(EMPTY_REGISTER_FORM);
    expect(store.isSubmitting()).toBe(true);
    expect(store.isBusy()).toBe(true);
    expect(store.submitLabel()).toBe('Creando cuenta técnica…');

    await vi.advanceTimersByTimeAsync(1000);
    await pending;

    expect(store.isSuccess()).toBe(true);
    expect(store.submitLabel()).toBe('Cuenta Creada');
  });

  it('rejects a second submit while one is still in flight', async () => {
    vi.useFakeTimers();

    const first = store.register(EMPTY_REGISTER_FORM);
    const second = await store.register(EMPTY_REGISTER_FORM);
    expect(second).toBe(false);

    await vi.advanceTimersByTimeAsync(1000);
    await first;
  });
});
