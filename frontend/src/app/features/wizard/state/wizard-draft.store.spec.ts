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

  it('starts the step 3 restrictions with the defaults', () => {
    expect(store.energia()).toBe('red-electrica');
    expect(store.tanqueL()).toBeNull();
    expect(store.presupuestoBs()).toBeNull();
    expect(store.presupuestoBajoElPiso()).toBe(false);
    expect(store.aPayload().restricciones).toEqual({
      energia: 'red-electrica',
      tanque_l: null,
      presupuesto_bs: null,
    });
  });

  it('keeps the restrictions across a reload', () => {
    store.setEnergia('solar');
    store.setTanqueL(5000);
    store.setPresupuestoBs('1500');

    const otro = TestBed.inject(WizardDraftStore);
    otro.cargar('p-1');

    expect(otro.energia()).toBe('solar');
    expect(otro.tanqueL()).toBe(5000);
    expect(otro.presupuestoBs()).toBe(1500);
  });

  it('keeps a budget below the floor out of the payload and flags it', () => {
    store.setPresupuestoBs('50');

    expect(store.presupuestoBajoElPiso()).toBe(true);
    expect(store.presupuestoEfectivo()).toBeNull();
    expect(store.aPayload().restricciones.presupuesto_bs).toBeNull();
  });

  it('accepts a budget at or above the floor and ignores empty input', () => {
    store.setPresupuestoBs('100');
    expect(store.aPayload().restricciones.presupuesto_bs).toBe(100);

    store.setPresupuestoBs('');
    expect(store.presupuestoBs()).toBeNull();
    expect(store.presupuestoBajoElPiso()).toBe(false);
    expect(store.aPayload().restricciones.presupuesto_bs).toBeNull();
  });

  it('loads a draft saved before step 3 with the default restrictions', () => {
    localStorage.setItem(
      'agroplan.borrador',
      JSON.stringify({ proyectoId: 'p-1', productos: [], siembra: '2026-12-01' }),
    );

    store.cargar('p-1');

    expect(store.siembra()).toBe('2026-12-01');
    expect(store.energia()).toBe('red-electrica');
    expect(store.tanqueL()).toBeNull();
    expect(store.presupuestoBs()).toBeNull();
  });
});
