import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { routes } from '../../app.routes';
import { SESSION_STORAGE_KEY } from '../../features/auth/auth.model';
import { authGuard } from './auth.guard';

const UNGUARDED_BY_DESIGN = ['', 'login', 'register', '**'];

describe('route protection', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [provideRouter(routes)] });
  });

  afterEach(() => localStorage.clear());

  it('guards the projects and terrain routes', () => {
    for (const path of ['projects', 'terreno']) {
      const route = routes.find((candidate) => candidate.path === path);
      expect(route?.canActivate).toEqual([authGuard]);
    }
  });

  it('leaves no other route unprotected', () => {
    const unprotected = routes
      .filter((route) => !route.canActivate)
      .map((route) => route.path ?? '')
      .filter((path) => !UNGUARDED_BY_DESIGN.includes(path));

    expect(unprotected).toEqual([]);
  });

  it('redirects an unauthenticated visit to /login keeping the returnUrl', async () => {
    const router = TestBed.inject(Router);

    await router.navigateByUrl('/projects');

    expect(router.url.startsWith('/login')).toBe(true);
    expect(router.url).toContain('returnUrl=%2Fprojects');
  });

  it('treats a tampered session payload as no session', async () => {
    localStorage.setItem(SESSION_STORAGE_KEY, 'not-json');
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [provideRouter(routes)] });
    const router = TestBed.inject(Router);

    await router.navigateByUrl('/terreno');

    expect(router.url.startsWith('/login')).toBe(true);
    expect(new URL('http://x' + router.url).searchParams.get('returnUrl')).toBe('/terreno');
  });
});
