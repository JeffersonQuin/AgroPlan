import { RenderMode, ServerRoute } from '@angular/ssr';

/**
 * Guarded routes cannot be prerendered: at build time there is no session, so
 * `authGuard` redirects and the prerendered HTML would come out empty. They are
 * rendered on the client, where the guard can read the stored session.
 */
export const serverRoutes: ServerRoute[] = [
  { path: 'projects', renderMode: RenderMode.Client },
  { path: 'terreno', renderMode: RenderMode.Client },
  {
    path: '**',
    renderMode: RenderMode.Prerender,
  },
];
