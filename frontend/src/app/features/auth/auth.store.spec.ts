import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { SESSION_STORAGE_KEY, TokenResponse } from './auth.model';
import { AuthStore } from './auth.store';

const TOKEN_RESPONSE: TokenResponse = {
  access_token: 'jwt-token',
  token_type: 'bearer',
  usuario: {
    id: 7,
    email: 'agronomo@agroplan.com',
    nombre: 'Ing. Rossi',
    foto_url: null,
    rol: 'cliente',
    activo: true,
    ultimo_acceso: null,
  },
};

describe('AuthStore', () => {
  let store: AuthStore;
  let http: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(AuthStore);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    localStorage.clear();
  });

  it('starts without a session', () => {
    expect(store.isAuthenticated()).toBe(false);
    expect(store.user()).toBeNull();
    expect(store.token()).toBeNull();
  });

  it('exchanges the Google id token and persists the session', () => {
    let result: boolean | undefined;
    store.loginWithGoogle('google-id-token').subscribe((ok) => (result = ok));

    expect(store.isSubmitting()).toBe(true);

    const request = http.expectOne('http://localhost:8000/auth/google');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ id_token: 'google-id-token' });
    request.flush(TOKEN_RESPONSE);

    expect(result).toBe(true);
    expect(store.isAuthenticated()).toBe(true);
    expect(store.token()).toBe('jwt-token');
    expect(store.user()?.email).toBe('agronomo@agroplan.com');
    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toContain('jwt-token');
  });

  it('hits the register endpoint when creating the account', () => {
    let result: boolean | undefined;
    store.registerWithGoogle('google-id-token').subscribe((ok) => (result = ok));

    const request = http.expectOne('http://localhost:8000/auth/google/register');
    request.flush(TOKEN_RESPONSE);

    expect(result).toBe(true);
    expect(store.isAuthenticated()).toBe(true);
  });

  it('surfaces the backend detail when the exchange fails', () => {
    let result: boolean | undefined;
    store.loginWithGoogle('bad-token').subscribe((ok) => (result = ok));

    http
      .expectOne('http://localhost:8000/auth/google')
      .flush({ detail: 'Token de Google inválido' }, { status: 401, statusText: 'Unauthorized' });

    expect(result).toBe(false);
    expect(store.status()).toBe('error');
    expect(store.error()).toBe('Token de Google inválido');
    expect(store.isAuthenticated()).toBe(false);
  });

  it('restores the session from localStorage', () => {
    localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({ token: 'persisted', user: TOKEN_RESPONSE.usuario }),
    );
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [] });
    const restored = TestBed.inject(AuthStore);

    expect(restored.isAuthenticated()).toBe(true);
    expect(restored.token()).toBe('persisted');
  });

  it('clears the session on logout', () => {
    localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({ token: 'persisted', user: TOKEN_RESPONSE.usuario }),
    );
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    const restored = TestBed.inject(AuthStore);

    restored.logout();

    expect(restored.isAuthenticated()).toBe(false);
    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });

  it('exposes the login copy', () => {
    expect(store.copy.title).toBe('Bienvenido de nuevo');
    expect(store.submitLabel()).toBe('Iniciar Sesión con Google');
  });
});
