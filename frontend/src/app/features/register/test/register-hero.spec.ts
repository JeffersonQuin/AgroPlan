import { TestBed } from '@angular/core/testing';
import { RegisterHero } from '../components/register-hero/register-hero';

/**
 * The hero resolves its four capability icons through a map of registry keys.
 * A name that does not exist in the registry does not throw: `NgIcon` warns and
 * leaves the element empty, so the only observable failure is a missing `<svg>`.
 */
describe('RegisterHero', () => {
  async function render() {
    const fixture = TestBed.createComponent(RegisterHero);
    await fixture.whenStable();
    return fixture;
  }

  function icons(fixture: { nativeElement: HTMLElement }): HTMLElement[] {
    return Array.from(fixture.nativeElement.querySelectorAll('ng-icon'));
  }

  it('draws the pill icon and one icon per capability', async () => {
    const fixture = await render();

    expect(icons(fixture)).toHaveLength(5);
  });

  it('draws an inline SVG for every icon', async () => {
    const fixture = await render();

    const empty = icons(fixture).filter((icon) => icon.querySelector('svg') === null);
    expect(empty).toHaveLength(0);
  });
});
