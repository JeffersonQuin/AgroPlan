import { TestBed } from '@angular/core/testing';
import { ProjectCard } from '../components/project-card/project-card';
import { PROJECT_FIXTURES } from '../data/project.fixtures';

describe('ProjectCard', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [ProjectCard] }).compileComponents();
  });

  async function render(index: number) {
    const fixture = TestBed.createComponent(ProjectCard);
    fixture.componentRef.setInput('project', PROJECT_FIXTURES[index]);
    await fixture.whenStable();
    return fixture;
  }

  it('renders the project identity and its derived area', async () => {
    const fixture = await render(0);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Mi parcela');
    expect(text).toContain('Valle Central');
    expect(text).toContain('21/11 11:06');
    expect(text).toContain('0,32 ha (3.200 m²)');
    expect(text).toContain('2 cultivos');
    expect(text).toContain('2 sectores');
  });

  it('labels a completed project with its status and next action', async () => {
    const fixture = await render(0);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Cómputo listo');
    expect(text).toContain('Abrir proyecto');
  });

  it('labels an in-progress project with the step it resumes', async () => {
    const fixture = await render(1);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Falta cálculo hidráulico');
    expect(text).toContain('Continuar (Paso 2)');
    expect(text).toContain('1,10 ha (11.000 m²)');
  });

  it('draws one block per crop inside the preview', async () => {
    const fixture = await render(0);
    const rects = fixture.nativeElement.querySelectorAll('app-project-preview rect[fill]');

    // Two crops plus the parcel border rectangle.
    expect(rects.length).toBeGreaterThanOrEqual(3);
  });

  it('emits the project when the primary action is used', async () => {
    const fixture = await render(0);
    let emitted: unknown;

    fixture.componentInstance.open.subscribe((project) => (emitted = project));
    const action = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.includes('Abrir proyecto'))!;

    action.click();

    expect(emitted).toBe(PROJECT_FIXTURES[0]);
  });
});
