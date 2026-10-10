import { describe, expect, it } from 'vitest';
import { decodeTerritories, decodePeople, namesFor } from './data';

describe('decodePeople', () => {
	const raw = {
		names: ['Jean DUPONT', 'Anne MARTIN', 'Luc BLOC'],
		t: { FR: ['LR', 1], 'DEP-02': ['LR', 2] },
		c: { 'COM-1': ['DVG', 0, 30, 'LR', 1, 50] }
	};
	it('expands unique names of aggregated territories', () => {
		const p = decodePeople('e', raw);
		expect(p.names.FR).toEqual({ 'e.LR': 'Anne MARTIN' });
		expect(p.names['DEP-02']).toEqual({ 'e.LR': 'Luc BLOC' });
	});
	it('expands the lists of a commune one by one, with their votes', () => {
		expect(decodePeople('e', raw).lists['COM-1']).toEqual([
			{ listId: 'e.DVG', person: 'Jean DUPONT', voix: 30 },
			{ listId: 'e.LR', person: 'Anne MARTIN', voix: 50 }
		]);
	});
	it('falls back on the country names for a territory without its own', () => {
		const p = decodePeople('e', raw);
		expect(namesFor(p, 'DEP-01')).toEqual({ 'e.LR': 'Anne MARTIN' });
		expect(namesFor(p, 'DEP-02')).toEqual({ 'e.LR': 'Luc BLOC' });
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
