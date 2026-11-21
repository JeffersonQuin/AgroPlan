import { TestBed } from '@angular/core/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';
import { AuthStore } from '../../features/auth/auth.store';
import { SESSION_STORAGE_KEY } from '../../features/auth/auth.model';
import { authGuard } from './auth.guard';

const ROUTE = { path: 'projects' } as never;
const STATE = { url: '/projects' } as never;

describe('authGuard', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
  });

  afterEach(() => localStorage.clear());

  it('redirects to /login keeping the requested url when there is no session', () => {
    const result = TestBed.runInInjectionContext(() => authGuard(ROUTE, STATE));

    expect(result instanceof UrlTree).toBe(true);
    const url = TestBed.inject(Router).serializeUrl(result as UrlTree);
    expect(url).toBe('/login?returnUrl=%2Fprojects');
  });

  it('allows the route when a session exists', () => {
    localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        token: 'jwt-token',
        user: {
          id: 7,
          email: 'agronomo@agroplan.com',
          nombre: null,
          foto_url: null,
          rol: 'cliente',
          activo: true,
          ultimo_acceso: null,
        },
      }),
    );
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    expect(TestBed.inject(AuthStore).isAuthenticated()).toBe(true);

    const result = TestBed.runInInjectionContext(() => authGuard(ROUTE, STATE));

    expect(result).toBe(true);
  });
});
