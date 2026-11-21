import { Routes } from '@angular/router';

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
  { path: '**', redirectTo: 'login' },
];
