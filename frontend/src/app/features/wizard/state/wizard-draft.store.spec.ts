import { TestBed } from '@angular/core/testing';
import { WizardDraftStore } from './wizard-draft.store';

describe('WizardDraftStore', () => {
  let store: WizardDraftStore;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({});
    store = TestBed.inject(WizardDraftStore);
    store.cargar('p-1');
  });

  it('starts empty with the sowing date set to today', () => {
    expect(store.vacio()).toBe(true);
    expect(store.cantidad()).toBe(0);
    expect(store.siembra()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it('collects products without touching the API', () => {
    store.agregarProducto('papa', '', 'Papa', '#8D6E63');
    store.agregarProducto(null, 'yuca', 'yuca', '#4CAF50');

    expect(store.cantidad()).toBe(2);
    // Papa va por código; yuca, que no está en el catálogo, por texto.
    expect(store.aPayload().productos).toEqual([
      { cultivo_codigo: 'papa' },
      { producto_texto: 'yuca' },
    ]);
  });

  it('ignores duplicates and names that are too short', () => {
    store.agregarProducto('papa', '', 'Papa', '#8D6E63');
    store.agregarProducto('papa', '', 'Papa', '#8D6E63');
    store.agregarProducto(null, 'y', 'y', '#4CAF50');

    expect(store.cantidad()).toBe(1);
  });

  it('keeps the sowing date and the list across a reload', () => {
    store.agregarProducto('lechuga', '', 'Lechuga', '#7CB342');
    store.setSiembra('2026-12-01');

    const otro = TestBed.inject(WizardDraftStore);
    otro.cargar('p-1');

    expect(otro.cantidad()).toBe(1);
    expect(otro.siembra()).toBe('2026-12-01');
  });

  it('does not mix projects', () => {
    store.agregarProducto('papa', '', 'Papa', '#8D6E63');

    store.cargar('p-2');

    expect(store.vacio()).toBe(true);
  });

  it('removes a product by position', () => {
    store.agregarProducto('papa', '', 'Papa', '#8D6E63');
    store.agregarProducto('lechuga', '', 'Lechuga', '#7CB342');

    store.quitarProducto(0);

    expect(store.productos().map((producto) => producto.etiqueta)).toEqual(['Lechuga']);
  });
});
