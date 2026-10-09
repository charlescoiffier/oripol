import { describe, expect, it } from 'vitest';
import { NO_DATA_COLOR, SCORE_DOMAIN, scoreColor } from './color';

const rgb = (css: string): number[] => {
	if (css.startsWith('#')) return [1, 3, 5].map((i) => parseInt(css.slice(i, i + 2), 16));
	return (css.match(/\d+(\.\d+)?/g) ?? []).map(Number).slice(0, 3);
};
const distance = (a: string, b: string): number =>
	rgb(a).reduce((sum, v, i) => sum + Math.abs(v - rgb(b)[i]), 0);

describe('scoreColor', () => {
	it('returns the no-data color for null', () => {
		expect(scoreColor(null)).toBe(NO_DATA_COLOR);
	});
	it('saturates at the display domain, which is narrower than the axis', () => {
		expect(SCORE_DOMAIN).toBeLessThan(2);
		expect(scoreColor(-5)).toBe(scoreColor(-SCORE_DOMAIN));
		expect(scoreColor(-SCORE_DOMAIN)).not.toBe(scoreColor(-SCORE_DOMAIN / 2));
	});
	it('is distinct at both extremes', () => {
		expect(scoreColor(-SCORE_DOMAIN)).not.toBe(scoreColor(SCORE_DOMAIN));
	});
	it('never confuses a centrist score with missing data', () => {
		for (const s of [0, 0.05, -0.05]) {
			expect(distance(scoreColor(s), NO_DATA_COLOR)).toBeGreaterThan(120);
		}
	});
});
