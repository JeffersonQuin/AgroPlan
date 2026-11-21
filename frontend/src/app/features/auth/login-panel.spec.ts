import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AuthStore } from './auth.store';
import { LoginPanel } from './login-panel';

describe('LoginPanel', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginPanel],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
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
    expect(fixture.nativeElement.querySelector('[aria-current="page"]')!.textContent).toContain(
      'Iniciar Sesión',
    );
  });

  it('navigates to the register screen instead of switching a mode', async () => {
    const fixture = await render();
    const registerLink = fixture.nativeElement.querySelector('a[href="/register"]');

    expect(registerLink).not.toBeNull();
    expect(registerLink.textContent).toContain('Crear Cuenta');
  });


});
