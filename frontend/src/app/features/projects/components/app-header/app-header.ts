import { Component, ElementRef, computed, inject, output, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { matAddOutline, matAgricultureOutline } from '@ng-icons/material-symbols/outline';
import { AuthStore } from '../../../auth/auth.store';

/** Fixed application header: brand link, primary action and the session menu. */
@Component({
  selector: 'app-header',
  imports: [NgIcon, RouterLink],
  viewProviders: [provideIcons({ matAddOutline, matAgricultureOutline })],
  host: {
    '(document:click)': 'closeMenu()',
    '(document:keydown.escape)': 'closeMenu()',
  },
  template: `
    <header
      class="fixed top-0 left-0 right-0 z-50 bg-surface-container-lowest border-b border-outline-variant/40"
    >
      <div
        class="h-16 w-full px-4 sm:px-space-lg lg:px-margin-desktop flex items-center justify-between gap-space-sm sm:gap-space-md lg:gap-space-lg"
      >
        <div class="flex items-center gap-space-md shrink-0">
          <a
            class="inline-flex items-center gap-1.5 text-primary rounded-lg"
            routerLink="/projects"
            aria-label="AgroPlan · Ir a mis proyectos"
          >
            <ng-icon name="matAgricultureOutline" size="26" aria-hidden="true" />
            <span class="text-headline-md">AgroPlan</span>
          </a>
          <div class="hidden xl:flex flex-col">
            <span class="text-label-sm text-on-surface-variant"
              >Diseño y planificación agrícola</span
            >
          </div>
        </div>

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

          <div
            class="relative flex items-center pl-space-xs border-l border-outline-variant/40"
            (click)="$event.stopPropagation()"
          >
            @if (user(); as usuario) {
              <button
                class="flex items-center gap-space-sm rounded-lg p-1 hover:bg-surface-bright transition-colors"
                type="button"
                aria-haspopup="menu"
                [attr.aria-expanded]="menuOpen()"
                aria-controls="menu-cuenta"
                aria-label="Abrir menú de cuenta"
                (click)="toggleMenu()"
              >
                <span
                  class="w-8 h-8 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center text-label-md ring-1 ring-outline-variant/60"
                  aria-hidden="true"
                  >{{ initials() }}</span
                >
                <div class="hidden xl:flex flex-col text-left">
                  <span class="text-label-md text-on-surface">{{ displayName() }}</span>
                  <span class="text-label-sm text-on-surface-variant">{{ usuario.rol }}</span>
                </div>
              </button>

              @if (menuOpen()) {
                <div
                  id="menu-cuenta"
                  role="menu"
                  aria-label="Cuenta"
                  class="absolute right-0 top-full mt-2 w-48 py-1 bg-surface-container-lowest rounded-lg border border-outline-variant/40 shadow-lg"
                >
                  <button
                    class="w-full px-space-md py-2 text-left text-body-md text-on-surface hover:bg-surface-bright transition-colors"
                    type="button"
                    role="menuitem"
                    (click)="logout()"
                  >
                    Cerrar sesión
                  </button>
                </div>
              }
            } @else {
              <div class="flex items-center gap-space-sm">
                <span
                  class="w-8 h-8 rounded-full bg-surface-container-high text-on-surface-variant flex items-center justify-center text-label-md ring-1 ring-outline-variant/60"
                  aria-hidden="true"
                  >?</span
                >
                <div class="hidden xl:flex flex-col text-left">
                  <span class="text-label-md text-on-surface">Invitado</span>
                  <span class="text-label-sm text-on-surface-variant">Sin sesión</span>
                </div>
              </div>
            }
          </div>
        </div>
      </div>
    </header>
  `,
})
export class AppHeader {
  readonly newProject = output<void>();

  private readonly auth = inject(AuthStore);
  private readonly router = inject(Router);
  private readonly host = inject(ElementRef) as ElementRef<HTMLElement>;

  readonly user = this.auth.user;
  readonly menuOpen = signal(false);

  readonly displayName = computed(() => {
    const usuario = this.user();
    if (!usuario) return '';
    return usuario.nombre?.trim() || usuario.email;
  });

  readonly initials = computed(() => initialsOf(this.displayName()));

  toggleMenu(): void {
    this.menuOpen.update((open) => !open);
  }

  closeMenu(): void {
    if (!this.menuOpen()) return;
    this.menuOpen.set(false);
    const trigger = this.host.nativeElement.querySelector<HTMLElement>(
      'button[aria-haspopup="menu"]',
    );
    trigger?.focus();
  }

  logout(): void {
    this.menuOpen.set(false);
    this.auth.logout();
    void this.router.navigate(['/login']);
  }
}

/** Two letters from the first and last word of the session name. */
function initialsOf(name: string): string {
  const words = name.split(/\s+/).filter((word) => word.length > 0);
  if (words.length === 0) return '?';
  const first = words[0][0] ?? '';
  const last = words.length > 1 ? (words[words.length - 1][0] ?? '') : '';
  return `${first}${last}`.toUpperCase();
}
