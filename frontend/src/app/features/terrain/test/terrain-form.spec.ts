import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { TerrainForm } from '../components/terrain-form/terrain-form';
import { TerrainStore } from '../state/terrain.store';

describe('TerrainForm', () => {
  let store: TerrainStore;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TerrainForm],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    store = TestBed.inject(TerrainStore);
  });

  async function render() {
    const fixture = TestBed.createComponent(TerrainForm);
    await fixture.whenStable();
    return fixture;
  }

  it('renders the three shapes and marks the active one', async () => {
    const fixture = await render();
    const buttons = fixture.nativeElement.querySelectorAll(
      '.grid-cols-3 button',
    ) as NodeListOf<HTMLButtonElement>;

    expect(buttons.length).toBe(3);
    expect(buttons[1].textContent).toContain('Trapecio');
    expect(buttons[1].getAttribute('aria-pressed')).toBe('true');
    expect(buttons[0].getAttribute('aria-pressed')).toBe('false');
  });

  it('switches the shape when another one is picked', async () => {
    const fixture = await render();
    const buttons = fixture.nativeElement.querySelectorAll(
      '.grid-cols-3 button',
    ) as NodeListOf<HTMLButtonElement>;

    buttons[0].click();
    await fixture.whenStable();

    expect(store.shape()).toBe('rectangulo');
    expect(buttons[0].getAttribute('aria-pressed')).toBe('true');
  });

  it('updates the store when a cota is edited', async () => {
    const fixture = await render();
    const input = fixture.nativeElement.querySelector(
      '#parcela-nombre',
    ) as HTMLInputElement;

    input.value = 'Parcela Sur';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await fixture.whenStable();

    expect(store.name()).toBe('Parcela Sur');
  });

  it('recomputes the diagonal when a cota changes', async () => {
    const fixture = await render();
    const inputs = fixture.nativeElement.querySelectorAll(
      'input[type="number"]',
    ) as NodeListOf<HTMLInputElement>;

    // First four number inputs are the cotas: top, bottom, left, right.
    inputs[0].value = '50';
    inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).not.toContain('42.40 m');
    expect(fixture.nativeElement.textContent).toContain(store.diagonalLabel());
  });

  it('builds the soil options from the loaded catalogue', async () => {
    const fixture = await render();

    // Sin catálogo (la API no respondió) cae en la lista local de respaldo.
    const opciones = Array.from(
      fixture.nativeElement.querySelectorAll('#tipo-suelo option') as NodeListOf<HTMLOptionElement>,
    ).map((opcion) => opcion.value);

    expect(opciones).toEqual(['franco', 'arenoso', 'arcilloso', 'limoso']);
  });

  it('updates the infiltration badge with the soil', async () => {
    const fixture = await render();
    const select = fixture.nativeElement.querySelector('#tipo-suelo') as HTMLSelectElement;

    expect(fixture.nativeElement.textContent).toContain('Infiltración: 15-25 mm/h');

    select.value = 'arcilloso';
    select.dispatchEvent(new Event('change', { bubbles: true }));
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('Infiltración: < 8 mm/h');
  });

  it('shows the assumed slope first and reveals the control on demand', async () => {
    const fixture = await render();

    expect(fixture.nativeElement.textContent).toContain('Asumimos');
    expect(fixture.nativeElement.querySelector('#pendiente-terreno')).toBeNull();

    const conocer = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.includes('La conozco'))!;
    conocer.click();
    await fixture.whenStable();

    expect(fixture.nativeElement.querySelector('#pendiente-terreno')).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain('1.0 %');
  });

  it('shows the slope badge and updates it from the range', async () => {
    const fixture = await render();
    // La pendiente arranca asumida: hay que decir que la conocemos para ver el control.
    Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    )
      .find((button) => button.textContent?.includes('La conozco'))!
      .click();
    await fixture.whenStable();

    const range = fixture.nativeElement.querySelector(
      'input[type="range"]',
    ) as HTMLInputElement;

    expect(fixture.nativeElement.textContent).toContain('1.0 %');

    range.value = '3';
    range.dispatchEvent(new Event('input', { bubbles: true }));
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('3.0 %');
  });
});
