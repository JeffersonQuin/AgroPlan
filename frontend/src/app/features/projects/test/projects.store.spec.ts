import { TestBed } from '@angular/core/testing';
import { ProjectsStore } from '../state/projects.store';

describe('ProjectsStore', () => {
  let store: ProjectsStore;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    store = TestBed.inject(ProjectsStore);
  });

  it('seeds the three demo projects', () => {
    expect(store.projects().length).toBe(3);
    expect(store.counts()).toEqual({ all: 3, completed: 1, in_progress: 2 });
  });

  it('sorts by most recent by default', () => {
    expect(store.visibleProjects().map((project) => project.name)).toEqual([
      'Mi parcela',
      'Parcela Norte',
      'Finca El Paraíso - B',
    ]);
  });

  it('filters by status', () => {
    store.setFilter('completed');
    expect(store.visibleProjects().map((project) => project.name)).toEqual(['Mi parcela']);

    store.setFilter('in_progress');
    expect(store.visibleProjects().length).toBe(2);
  });

  it('sorts by area descending', () => {
    store.setSort('area_desc');
    expect(store.visibleProjects()[0].name).toBe('Parcela Norte');
  });

  it('sorts alphabetically', () => {
    store.setSort('name');
    expect(store.visibleProjects()[0].name).toBe('Finca El Paraíso - B');
  });

  it('searches by project name', () => {
    store.setSearch('norte');
    expect(store.visibleProjects().map((project) => project.name)).toEqual(['Parcela Norte']);
  });

  it('searches by crop name', () => {
    store.setSearch('lechuga');
    expect(store.visibleProjects().map((project) => project.name)).toEqual(['Mi parcela']);
  });

  it('searches by location and hydraulic specs', () => {
    store.setSearch('luján');
    expect(store.visibleProjects().length).toBe(1);

    store.setSearch('canal de riego');
    expect(store.visibleProjects().map((project) => project.name)).toEqual(['Parcela Norte']);
  });

  it('combines the search term with the status filter', () => {
    store.setFilter('completed');
    store.setSearch('norte');
    expect(store.visibleProjects()).toEqual([]);
  });

  it('creates a project at the head of the list', () => {
    const created = store.create({ name: '  Los Olivos ', location: '', unitSystem: 'metric' });

    expect(created.name).toBe('Los Olivos');
    expect(created.location).toBe('Sin ubicación');
    expect(created.status).toBe('in_progress');
    expect(created.areaM2).toBe(0);
    expect(store.projects().length).toBe(4);
    expect(store.counts().all).toBe(4);
    expect(store.visibleProjects()[0].name).toBe('Los Olivos');
  });
});
