import { TestBed } from '@angular/core/testing';
import { AuthStore } from './auth.store';
import { LoginPanel } from './login-panel';

describe('LoginPanel', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [LoginPanel] }).compileComponents();
  });

  async function render() {
    const fixture = TestBed.createComponent(LoginPanel);
    await fixture.whenStable();
    return fixture;
  }

  it('starts on the login view', async () => {
    const fixture = await render();
    const heading = fixture.nativeElement.querySelector('h1') as HTMLElement;

    expect(heading.textContent).toContain('Bienvenido de nuevo');
    expect(fixture.nativeElement.querySelector('#tab-login')!.getAttribute('aria-selected')).toBe(
      'true',
    );
  });

  it('switches to the register view when the second tab is clicked', async () => {
    const fixture = await render();
    const registerTab = fixture.nativeElement.querySelector('#tab-register') as HTMLButtonElement;

    registerTab.click();
    await fixture.whenStable();

    const heading = fixture.nativeElement.querySelector('h1') as HTMLElement;
    expect(heading.textContent).toContain('Crea tu cuenta técnica');
    expect(registerTab.getAttribute('aria-selected')).toBe('true');
    expect(fixture.nativeElement.querySelector('#input-name')).not.toBeNull();
  });

  it('hides the name field again when returning to login', async () => {
    const fixture = await render();

    (fixture.nativeElement.querySelector('#tab-register') as HTMLButtonElement).click();
    await fixture.whenStable();

    (fixture.nativeElement.querySelector('#tab-login') as HTMLButtonElement).click();
    await fixture.whenStable();

    expect(fixture.nativeElement.querySelector('#input-name')).toBeNull();
  });

  it('shows the jury notice only after the demo credentials are loaded', async () => {
    const fixture = await render();
    const store = TestBed.inject(AuthStore);

    expect(fixture.nativeElement.textContent).not.toContain('Credenciales del Jurado cargadas');

    store.demoCredentials();
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('Credenciales del Jurado cargadas');
  });
});
