import { describe, expect, it } from 'vitest';
import { decodeTerritories, decodePeople } from './data';

describe('decodePeople', () => {
	it('expands the packed file into territory -> list id -> name', () => {
		const p = decodePeople('e', { names: ['Jean DUPONT', 'Anne MARTIN'], t: { 'COM-1': ['DVG', 0, 'LR', 1], FR: ['LR', 1] } });
		expect(p['COM-1']).toEqual({ 'e.DVG': 'Jean DUPONT', 'e.LR': 'Anne MARTIN' });
		expect(p.FR).toEqual({ 'e.LR': 'Anne MARTIN' });
	});
});

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
