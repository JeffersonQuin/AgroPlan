import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  {
    path: 'login',
    title: 'Ingresar · AgroPlan',
    loadComponent: () =>
      import('./features/auth/login.page').then((m) => m.LoginPage),
  },
  {
    path: 'register',
    title: 'Crear cuenta · AgroPlan',
    loadComponent: () =>
      import('./features/register/register.page').then((m) => m.RegisterPage),
  },
  {
    path: 'projects',
    title: 'Mis proyectos · AgroPlan',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/projects/projects.page').then((m) => m.ProjectsPage),
  },
  {
    path: 'proyectos/:proyectoId/terreno',
    title: 'Terreno · AgroPlan',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/terrain/terrain.page').then((m) => m.TerrainPage),
  },
  {
    path: 'proyectos/:proyectoId/cultivos',
    title: 'Cultivos · AgroPlan',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/cultivos/cultivos.page').then((m) => m.CultivosPage),
  },
  {
    path: 'proyectos/:proyectoId/riego',
    title: 'Sistema de riego · AgroPlan',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/riego/riego.page').then((m) => m.RiegoPage),
  },
  { path: '**', redirectTo: 'login' },
];
