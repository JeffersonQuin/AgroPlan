import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { RegisterStore } from '../state/register.store';
import { RegisterForm } from '../components/register-form/register-form';

describe('RegisterForm', () => {
  let store: RegisterStore;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RegisterForm],
      providers: [provideRouter([])],
    }).compileComponents();
    store = TestBed.inject(RegisterStore);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function render() {
    const fixture = TestBed.createComponent(RegisterForm);
    await fixture.whenStable();
    return fixture;
  }

  type Fixture = Awaited<ReturnType<typeof render>>;

  function query<T extends Element>(fixture: Fixture, selector: string): T {
    return fixture.nativeElement.querySelector(selector) as T;
  }

  async function type(fixture: Fixture, selector: string, value: string) {
    const input = query<HTMLInputElement>(fixture, selector);
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await fixture.whenStable();
  }

  /** Browsers fire both `input` and `change` when a select option is picked. */
  async function selectRole(fixture: Fixture, value: string) {
    const select = query<HTMLSelectElement>(fixture, '#userRole');
    select.value = value;
    select.dispatchEvent(new Event('input', { bubbles: true }));
    select.dispatchEvent(new Event('change', { bubbles: true }));
    await fixture.whenStable();
  }

  async function acceptTerms(fixture: Fixture) {
    const checkbox = query<HTMLInputElement>(fixture, '#termsCheckbox');
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event('input', { bubbles: true }));
    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
    await fixture.whenStable();
  }

  async function fillIdentity(fixture: Fixture) {
    await type(fixture, '#fullName', 'Ing. Lucas Ferrero');
    await type(fixture, '#workEmail', 'lucas@agronomia-consulting.com');
    await selectRole(fixture, 'agronomo');
    await type(fixture, '#password', 'Abcdefg1!');
    await type(fixture, '#confirmPassword', 'Abcdefg1!');
  }

  async function submit(fixture: Fixture) {
    query<HTMLFormElement>(fixture, 'form').dispatchEvent(new Event('submit'));
    await fixture.whenStable();
  }

  it('renders every agronomic role option', async () => {
    const fixture = await render();
    const options = fixture.nativeElement.querySelectorAll(
      '#userRole option',
    ) as NodeListOf<HTMLOptionElement>;

    expect(options.length).toBe(6);
    expect(options[1].value).toBe('agronomo');
  });

  it('shows the required errors on an empty submit', async () => {
    const fixture = await render();

    await submit(fixture);

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Ingresá tu nombre completo.');
    expect(text).toContain('Ingresá tu correo profesional.');
    expect(text).toContain('Elegí tu rol o especialidad agronómica.');
    expect(store.status()).toBe('idle');
  });

  it('rejects a password shorter than eight characters', async () => {
    const fixture = await render();

    await type(fixture, '#password', 'Ab1!');
    await submit(fixture);

    expect(fixture.nativeElement.textContent).toContain(
      'La contraseña debe tener al menos 8 caracteres.',
    );
  });

  it('reports mismatched passwords', async () => {
    const fixture = await render();

    await type(fixture, '#password', 'Abcdefg1!');
    await type(fixture, '#confirmPassword', 'Distinta1!');

    expect(fixture.nativeElement.textContent).toContain('Las contraseñas no coinciden.');
  });

  it('blocks the submit when the terms are not accepted', async () => {
    const fixture = await render();
    await fillIdentity(fixture);

    await submit(fixture);

    expect(fixture.nativeElement.textContent).toContain(
      'Tenés que aceptar los términos para crear tu cuenta.',
    );
    expect(store.status()).toBe('idle');
  });

  it('updates the strength meter as the password changes', async () => {
    const fixture = await render();

    expect(fixture.nativeElement.textContent).toContain('Mínimo 8 caracteres');

    await type(fixture, '#password', 'Abcdefg1!');

    expect(fixture.nativeElement.textContent).toContain('Excelente (Robusta)');
  });

  it('registers with a complete and valid form', async () => {
    const fixture = await render();
    await fillIdentity(fixture);
    await acceptTerms(fixture);

    // Fake timers go in only after rendering: `whenStable()` needs real ones.
    vi.useFakeTimers();
    query<HTMLFormElement>(fixture, 'form').dispatchEvent(new Event('submit'));

    expect(store.isSubmitting()).toBe(true);

    await vi.advanceTimersByTimeAsync(1000);

    expect(store.isSuccess()).toBe(true);
  });
});
