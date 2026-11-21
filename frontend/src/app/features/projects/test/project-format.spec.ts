import { formatArea, formatModifiedAt, formatThousands, toLocalIso } from '../utils/project-format';

describe('project formatting', () => {
  it('groups thousands with a comma', () => {
    expect(formatThousands(3200)).toBe('3,200');
    expect(formatThousands(11000)).toBe('11,000');
    expect(formatThousands(0)).toBe('0');
  });

  it('formats the modified timestamp without a timezone', () => {
    expect(formatModifiedAt('2026-11-21T11:06:00')).toBe('21/11 11:06');
    expect(formatModifiedAt('2026-01-05T09:02:00')).toBe('05/01 09:02');
  });

  it('returns the raw value when the timestamp is malformed', () => {
    expect(formatModifiedAt('ayer')).toBe('ayer');
  });

  it('formats the area in metric units', () => {
    expect(formatArea(3200)).toBe('0.32 ha (3,200 m²)');
    expect(formatArea(11000)).toBe('1.10 ha (11,000 m²)');
  });

  it('formats the area in imperial units', () => {
    expect(formatArea(3200, 'imperial')).toBe('0.79 ac (34,445 ft²)');
  });

  it('builds a local ISO stamp with zero padding', () => {
    expect(toLocalIso(new Date(2026, 0, 5, 9, 2))).toBe('2026-01-05T09:02:00');
  });
});
