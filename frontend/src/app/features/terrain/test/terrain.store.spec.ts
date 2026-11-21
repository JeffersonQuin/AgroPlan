import { TestBed } from '@angular/core/testing';
import { TerrainStore } from '../state/terrain.store';

describe('TerrainStore', () => {
  let store: TerrainStore;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    store = TestBed.inject(TerrainStore);
  });

  it('starts with the mockup reference values', () => {
    expect(store.name()).toBe('Mi parcela');
    expect(store.shape()).toBe('trapecio');
    expect(store.areaHaLabel()).toBe('0.32 ha');
    expect(store.areaSqMLabel()).toBe('(3,200 m²)');
    expect(store.perimeterLabel()).toBe('172.4 m');
    expect(store.verticesLabel()).toBe('4 lados (trapecio)');
    expect(store.diagonalLabel()).toBe('42.40 m');
    expect(store.desnivelLabel()).toBe('0.60 m (1% pend.)');
    expect(store.slopeLabel()).toBe('1.0 %');
    expect(store.infiltrationLabel()).toBe('Infiltración: 15-25 mm/h');
  });

  it('replaces the reference metrics with real geometry when a cota changes', () => {
    store.setDimension('topM', 50);

    expect(store.metrics().areaM2).toBe(1800);
    expect(store.areaHaLabel()).toBe('0.18 ha');
  });

  it('derives the vertical drop from the slope', () => {
    store.setSlope(2.5);

    expect(store.desnivelLabel()).toBe('1.50 m (2.5% pend.)');
    expect(store.slopeLabel()).toBe('2.5 %');
  });

  it('follows the shape, soil and water source selections', () => {
    store.setShape('rectangulo');
    store.setSoil('arenoso');
    store.setWaterSource('cisterna');

    expect(store.verticesLabel()).toBe('4 lados (rectángulo)');
    expect(store.infiltrationLabel()).toBe('Infiltración: > 30 mm/h');
    expect(store.waterSource()).toBe('cisterna');
  });

  it('keeps the parcel identity and the water figures', () => {
    store.setName('Parcela Sur');
    store.setFlow(2.4);
    store.setStaticLevel(22);

    expect(store.name()).toBe('Parcela Sur');
    expect(store.flowM3h()).toBe(2.4);
    expect(store.staticLevelM()).toBe(22);
  });
});
