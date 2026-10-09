import { describe, expect, it } from 'vitest';
import { NO_DATA_COLOR, scoreColor } from './color';

describe('scoreColor', () => {
	it('returns the no-data color for null', () => {
		expect(scoreColor(null)).toBe(NO_DATA_COLOR);
	});
	it('is darker red at -2 than at -1 and clamps beyond bounds', () => {
		expect(scoreColor(-5)).toBe(scoreColor(-2));
		expect(scoreColor(-2)).not.toBe(scoreColor(-1));
	});
	it('is distinct at both extremes', () => {
		expect(scoreColor(-2)).not.toBe(scoreColor(2));
	});
});
