import { RenderMode } from '@angular/ssr';
import { routes } from './app.routes';
import { serverRoutes } from './app.routes.server';

/**
 * `npm run build` fails when a parameterized route falls through to the
 * prerender fallback: the build cannot enumerate project ids, so it stops with
 * "uses prerendering and includes parameters, but 'getPrerenderParams' is
 * missing". That is how `proyectos/:proyectoId/riego` broke the production
 * build while its two sibling wizard routes were declared.
 */
describe('serverRoutes', () => {
  const parameterized = routes.filter((route) => route.path?.includes(':'));

  it('declares every parameterized app route instead of letting it fall to the fallback', () => {
    expect(parameterized.length).toBeGreaterThan(0);

    for (const route of parameterized) {
      const declared = serverRoutes.find((server) => server.path === route.path);
      expect(declared, `falta ${route.path} en app.routes.server.ts`).toBeDefined();
    }
  });

  it('renders every parameterized app route on the client, never by prerendering it', () => {
    for (const route of parameterized) {
      const declared = serverRoutes.find((server) => server.path === route.path);
      expect(declared?.renderMode, `${route.path} no puede prerenderizarse`).toBe(RenderMode.Client);
    }
  });

  it('keeps prerendering for the static routes through the fallback', () => {
    expect(serverRoutes.at(-1)).toEqual({ path: '**', renderMode: RenderMode.Prerender });
  });
});
