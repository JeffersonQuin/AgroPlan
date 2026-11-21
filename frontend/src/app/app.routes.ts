import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  {
    path: 'login',
    title: 'Ingresar · AgroPlan',
    loadComponent: () =>
      import('./features/auth/login.page').then((m) => m.LoginPage),
  },
  { path: '**', redirectTo: 'login' },
];
