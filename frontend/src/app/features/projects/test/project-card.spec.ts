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

  it('renders the project identity and its area in the mockup format', async () => {
    const fixture = await render(0);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Mi parcela');
    expect(text).toContain('Valle Central');
    expect(text).toContain('21/11 11:06');
    expect(text).toContain('0.32 ha (3,200 m²)');
    expect(text).toContain('2 cultivos');
  });

  it('renders the irrigation summary and the hydraulic specs', async () => {
    const fixture = await render(0);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Riego por goteo');
    expect(text).toContain('2 sectores');
    expect(text).toContain('Pozo artesiano · Tanque 5.000 L · Bomba 1 HP');
  });

  it('overlays the wizard step and the dimensions on the schematic', async () => {
    const fixture = await render(0);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Paso 4: Resultado');
    expect(text).toContain('60.00 × 40.00 m');
  });

  it('draws the reference schematic for each fixture', async () => {
    const first = await render(0);
    expect(
      first.nativeElement.querySelectorAll('app-preview-mi-parcela polygon').length,
    ).toBeGreaterThan(1);

    const third = await render(2);
    const text = third.nativeElement.textContent as string;
    expect(text).toContain('Paso 3: Sistema');
    expect(text).toContain('0.75 ha (7,500 m²)');
    expect(third.nativeElement.querySelector('app-preview-finca-el-paraiso')).not.toBeNull();
  });

  it('labels a completed project with its status and next action', async () => {
    const fixture = await render(0);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Cómputo listo');
    expect(text).toContain('Abrir proyecto');
  });

  it('renders an inline SVG for every icon of the three fixtures', async () => {
    for (const index of [0, 1, 2]) {
      const fixture = await render(index);
      const icons = Array.from(
        fixture.nativeElement.querySelectorAll('ng-icon') as NodeListOf<HTMLElement>,
      );

      expect(icons.length).toBeGreaterThan(0);
      expect(icons.filter((icon) => icon.querySelector('svg') === null).length).toBe(0);
    }
  });

  it('labels an in-progress project with the step it resumes', async () => {
    const fixture = await render(1);
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Falta cálculo hidráulico');
    expect(text).toContain('Continuar (Paso 2)');
    expect(text).toContain('1.10 ha (11,000 m²)');
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
