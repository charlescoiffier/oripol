import { describe, expect, it } from 'vitest';
import { decodeTerritories } from './data';

describe('decodeTerritories', () => {
	it('turns compact rows into territory results', () => {
		const t = decodeTerritories({
			lists: ['e.A', 'e.B'],
			territories: { FR: [100, 80, 2, 3, 75, 50, 25] }
		});
		expect(t.FR).toEqual({
			inscrits: 100,
			votants: 80,
			blancs: 2,
			nuls: 3,
			exprimes: 75,
			voix: { 'e.A': 50, 'e.B': 25 },
			precision: 'commune'
		});
	});

	it('keeps zero votes out of the voix map', () => {
		const t = decodeTerritories({ lists: ['e.A', 'e.B'], territories: { X: [10, 5, 0, 0, 5, 5, 0] } });
		expect(t.X.voix).toEqual({ 'e.A': 5 });
	});
});
