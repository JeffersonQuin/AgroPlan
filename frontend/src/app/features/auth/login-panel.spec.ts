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
  });


});
