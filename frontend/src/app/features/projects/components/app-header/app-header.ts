import { Component, output } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matAddOutline,
  matAgricultureOutline,
  matNotificationsOutline,
} from '@ng-icons/material-symbols/outline';

/** Fixed application header: brand, primary navigation and the profile cluster. */
@Component({
  selector: 'app-header',
  imports: [NgIcon],
  viewProviders: [provideIcons({ matAddOutline, matAgricultureOutline, matNotificationsOutline })],
  template: `
    <header
      class="fixed top-0 left-0 right-0 z-50 bg-surface-container-lowest border-b border-outline-variant/40"
    >
      <div
        class="h-16 w-full px-4 sm:px-space-lg lg:px-margin-desktop flex items-center justify-between gap-space-sm sm:gap-space-md lg:gap-space-lg"
      >
        <div class="flex items-center gap-space-md shrink-0">
          <span class="inline-flex items-center gap-1.5 text-primary">
            <ng-icon name="matAgricultureOutline" size="26" aria-hidden="true" />
            <span class="text-headline-md">AgroPlan</span>
          </span>
          <div class="hidden xl:flex flex-col">
            <span class="text-label-sm text-on-surface-variant"
              >Diseño y planificación agrícola</span
            >
          </div>
        </div>

        <nav
          class="hidden lg:flex items-center gap-space-xs bg-surface-bright/70 px-space-xs py-1 rounded-xl border border-outline-variant/30"
        >
          <a
            class="px-space-md py-1.5 rounded-lg bg-surface-container-high text-on-surface text-headline-sm"
            href="#"
            aria-current="page"
            >Mis Proyectos</a
          >
          <a
            class="px-space-md py-1.5 rounded-lg text-body-md text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-colors"
            href="#"
            >Catálogo de Cultivos</a
          >
          <a
            class="px-space-md py-1.5 rounded-lg text-body-md text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-colors"
            href="#"
            >Calculadora Hidráulica</a
          >
          <a
            class="px-space-md py-1.5 rounded-lg text-body-md text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-colors"
            href="#"
            >Documentación</a
          >
        </nav>

        <div class="flex items-center gap-space-md shrink-0">
          <button
            class="inline-flex items-center gap-space-xs bg-primary-container text-on-primary text-label-md px-space-md py-2 rounded-lg hover:bg-primary transition-colors shadow-sm"
            type="button"
            (click)="newProject.emit()"
          >
            <ng-icon name="matAddOutline" size="18" aria-hidden="true" />
            <span class="hidden sm:inline">Nuevo proyecto</span>
          </button>

          <div
            class="hidden xl:flex items-center gap-1.5 px-space-sm py-1 bg-surface-bright rounded-full border border-outline-variant/40"
          >
            <span class="w-2 h-2 rounded-full bg-secondary"></span>
            <span class="text-label-sm text-on-surface-variant">En línea</span>
          </div>

          <button
            class="p-2 text-on-surface-variant hover:text-on-surface hover:bg-surface-bright rounded-lg transition-colors relative"
            type="button"
            aria-label="Notificaciones"
          >
            <ng-icon name="matNotificationsOutline" size="20" aria-hidden="true" />
            <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-error rounded-full"></span>
          </button>

          <div
            class="flex items-center gap-space-sm pl-space-xs border-l border-outline-variant/40"
          >
            <span
              class="w-8 h-8 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center text-label-md ring-1 ring-outline-variant/60"
              aria-hidden="true"
              >MR</span
            >
            <div class="hidden xl:flex flex-col text-left">
              <span class="text-label-md text-on-surface">Ing. Martín Rossi</span>
              <span class="text-label-sm text-on-surface-variant">Agrónomo Senior</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  `,
})
export class AppHeader {
  readonly newProject = output<void>();
}
