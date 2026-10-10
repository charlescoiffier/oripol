import { describe, expect, it } from 'vitest';
import { leader, resultRows } from './leader';
import type { Family, ListInfo, TerritoryResult } from './types';

const families = [
	{ id: 'gauche', label: 'Gauche', position: -1, color: '#f00' },
	{ id: 'droite', label: 'Droite', position: 1, color: '#00f' },
	{ id: 'non_classe', label: 'Non classé', position: null, color: '#ccc', inBase: false }
] as Family[];
const lists: Record<string, ListInfo> = {
	'e.A': { label: 'Alice (PS)', family: 'gauche' },
	'e.B': { label: 'Bob (LR)', family: 'droite' },
	'e.NC': { label: 'Sans étiquette', family: 'non_classe' }
};
const r = (voix: Record<string, number>, exprimes = 100): TerritoryResult => ({
	inscrits: 200, votants: 110, blancs: 4, nuls: 6, exprimes, voix, precision: 'commune'
});
const none = { positions: {}, listFamilies: {} };

describe('leader', () => {
	it('is the list with most votes among classified lists', () => {
		expect(leader(r({ 'e.A': 30, 'e.B': 45, 'e.NC': 25 }), lists, families, none)).toEqual({ listId: 'e.B', family: 'droite' });
	});
	it('ignores unclassified lists even when they are first', () => {
		expect(leader(r({ 'e.A': 10, 'e.B': 5, 'e.NC': 85 }), lists, families, none)?.listId).toBe('e.A');
	});
	it('follows the visitor reclassification', () => {
		const c = { positions: {}, listFamilies: { 'e.B': 'gauche' as const } };
		expect(leader(r({ 'e.A': 30, 'e.B': 45, 'e.NC': 25 }), lists, families, c)).toEqual({ listId: 'e.B', family: 'gauche' });
	});
	it('is null without any classified vote', () => {
		expect(leader(r({ 'e.NC': 100 }), lists, families, none)).toBeNull();
		expect(leader(r({}, 0), lists, families, none)).toBeNull();
	});
});

describe('resultRows', () => {
	it('sorts lists by votes with their share of the expressed votes', () => {
		const rows = resultRows(r({ 'e.A': 30, 'e.B': 45, 'e.NC': 25 }), lists, none);
		expect(rows.map((x) => x.listId)).toEqual(['e.B', 'e.A', 'e.NC']);
		expect(rows[0]).toMatchObject({ label: 'Bob (LR)', family: 'droite', voix: 45, share: 0.45 });
	});
	it('drops lists without votes', () => {
		expect(resultRows(r({ 'e.A': 0, 'e.B': 10 }, 10), lists, none).map((x) => x.listId)).toEqual(['e.B']);
	});
});
