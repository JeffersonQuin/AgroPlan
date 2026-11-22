import { RenderMode, ServerRoute } from '@angular/ssr';

/**
 * Guarded routes cannot be prerendered: at build time there is no session, so
 * `authGuard` redirects and the prerendered HTML would come out empty. They are
 * rendered on the client, where the guard can read the stored session. The wizard
 * routes also carry the project id, which prerendering cannot enumerate.
 */
export const serverRoutes: ServerRoute[] = [
  { path: 'projects', renderMode: RenderMode.Client },
  { path: 'proyectos/:proyectoId/terreno', renderMode: RenderMode.Client },
  {
    path: '**',
    renderMode: RenderMode.Prerender,
  },
];
