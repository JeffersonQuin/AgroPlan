import { TestBed } from '@angular/core/testing';
import { ProjectCreateModal } from '../components/project-create-modal/project-create-modal';
import { ProjectsStore } from '../state/projects.store';

describe('ProjectCreateModal', () => {
  let store: ProjectsStore;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [ProjectCreateModal] }).compileComponents();
    store = TestBed.inject(ProjectsStore);
  });

  async function render() {
    const fixture = TestBed.createComponent(ProjectCreateModal);
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

  it('starts on the metric system with an empty counter', async () => {
    const fixture = await render();

    expect(fixture.nativeElement.textContent).toContain('0 / 60');
    expect(
      Array.from(
        fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
      ).find((button) => button.textContent?.includes('Metros'))!.getAttribute('aria-pressed'),
    ).toBe('true');
  });

  it('updates the character counter as the name is typed', async () => {
    const fixture = await render();

    await type(fixture, '#projectName', 'Los Olivos');

    expect(fixture.nativeElement.textContent).toContain('10 / 60');
  });

  it('refuses to create a project without a name', async () => {
    const fixture = await render();

    query<HTMLFormElement>(fixture, 'form').dispatchEvent(new Event('submit'));
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('Poné un nombre para el proyecto.');
    expect(store.projects().length).toBe(3);
  });

  it('creates the project and asks to be closed', async () => {
    const fixture = await render();
    let closed = false;
    fixture.componentInstance.close.subscribe(() => (closed = true));

    await type(fixture, '#projectName', 'Los Olivos');
    await type(fixture, '#projectLocation', 'Valle Central');
    query<HTMLFormElement>(fixture, 'form').dispatchEvent(new Event('submit', { bubbles: true }));
    await fixture.whenStable();

    expect(store.projects().length).toBe(4);
    expect(store.projects()[0].name).toBe('Los Olivos');
    expect(store.projects()[0].location).toBe('Valle Central');
    expect(closed).toBe(true);
  });

  it('emits close when the dialog is dismissed', async () => {
    const fixture = await render();
    let closed = false;
    fixture.componentInstance.close.subscribe(() => (closed = true));

    const cancel = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.trim() === 'Cancelar')!;
    cancel.click();

    expect(closed).toBe(true);
  });
});
