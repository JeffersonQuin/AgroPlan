import {
  Component,
  ElementRef,
  afterNextRender,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { environment } from '../../../../../environments/environment';

interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleAccountsId {
  initialize(config: { client_id: string; callback: (response: GoogleCredentialResponse) => void }): void;
  renderButton(parent: HTMLElement, options: Record<string, string>): void;
}

declare global {
  interface Window {
    google?: { accounts: { id: GoogleAccountsId } };
  }
}

const GSI_SOURCE = 'https://accounts.google.com/gsi/client';

/**
 * `initialize()` is global in the GIS script, so it must run once per client id.
 * The callback is routed through this indirection so a remounted component
 * keeps receiving credentials without re-initialising.
 */
let initializedClientId = '';
let credentialHandler: (credential: string) => void = () => undefined;

/**
 * Google Identity Services button.
 *
 * Loads the GIS script on the browser, renders Google's own button and emits
 * the ID token. The ID token is what the backend exchanges for an access token.
 */
@Component({
  selector: 'app-google-sign-in',
  template: `
    @if (!configured) {
      <div
        class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-label-sm text-amber-900"
        role="alert"
      >
        Falta <code>googleClientId</code> en
        <code>src/environments/environment.ts</code>. Usá el mismo valor que
        <code>GOOGLE_CLIENT_ID</code> del backend y autorizá este origen en Google Cloud
        Console.
      </div>
    } @else if (failed()) {
      <div
        class="rounded-lg border border-error/40 bg-error-container px-3 py-2 text-label-sm text-on-error-container"
        role="alert"
      >
        No pudimos cargar el acceso de Google. Revisá la conexión y recargá.
      </div>
    } @else {
      <div class="flex justify-center" #host></div>
    }
  `,
})
export class GoogleSignIn {
  readonly credential = output<string>();

  protected readonly configured = environment.googleClientId.length > 0;
  protected readonly failed = signal(false);
  private readonly host = viewChild<ElementRef<HTMLElement>>('host');

  constructor() {
    afterNextRender(() => {
      if (this.configured) void this.mount();
    });
  }

  private async mount(): Promise<void> {
    try {
      await loadGsiScript();

      const accounts = window.google?.accounts.id;
      const element = this.host()?.nativeElement;
      if (!accounts || !element) {
        this.failed.set(true);
        return;
      }

      credentialHandler = (credential) => this.credential.emit(credential);

      if (initializedClientId !== environment.googleClientId) {
        accounts.initialize({
          client_id: environment.googleClientId,
          callback: (response) => credentialHandler(response.credential),
        });
        initializedClientId = environment.googleClientId;
      }
      accounts.renderButton(element, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'rectangular',
        logo_alignment: 'left',
        width: '320',
      });
    } catch {
      this.failed.set(true);
    }
  }
}

function loadGsiScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) {
      resolve();
      return;
    }

    const existing = document.querySelector<HTMLScriptElement>('script[data-gsi]');
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('gsi')), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.src = GSI_SOURCE;
    script.async = true;
    script.defer = true;
    script.dataset['gsi'] = 'true';
    script.addEventListener('load', () => resolve(), { once: true });
    script.addEventListener('error', () => reject(new Error('gsi')), { once: true });
    document.head.appendChild(script);
  });
}
