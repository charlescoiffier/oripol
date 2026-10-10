import { describe, expect, it } from 'vitest';
import { MIN_CLASSIFIED, NO_OVERRIDES, classifiedShare, familyShares, score } from './score';
import type { Family, ListInfo, TerritoryResult } from './types';

const families: Family[] = [
	{ id: 'extreme_gauche', label: 'EG', position: -2, color: '#000' },
	{ id: 'gauche', label: 'G', position: -1, color: '#000' },
	{ id: 'centre', label: 'C', position: 0, color: '#000' },
	{ id: 'droite', label: 'D', position: 1, color: '#000' },
	{ id: 'extreme_droite', label: 'ED', position: 2, color: '#000' },
	{ id: 'divers', label: 'Div', position: null, color: '#000' },
	{ id: 'regionaliste', label: 'Reg', position: null, color: '#000' },
	{ id: 'non_classe', label: 'NC', position: null, color: '#ccc', inBase: false }
];
const lists: Record<string, ListInfo> = {
	a: { label: 'A', family: 'gauche' },
	b: { label: 'B', family: 'droite' },
	c: { label: 'C', family: 'divers' },
	n: { label: 'N', family: 'non_classe' }
};
const result = (voix: Record<string, number>, exprimes: number): TerritoryResult => ({
	inscrits: 200,
	votants: 120,
	blancs: 10,
	nuls: 10,
	exprimes,
	voix,
	precision: 'commune'
});

describe('score', () => {
	it('is 0 when left and right are balanced', () => {
		expect(score(result({ a: 50, b: 50 }, 100), lists, families, NO_OVERRIDES)).toBeCloseTo(0);
	});

	it('dilutes the score with off-axis families but counts them in exprimes', () => {
		expect(score(result({ a: 50, c: 50 }, 100), lists, families, NO_OVERRIDES)).toBeCloseTo(-0.5);
	});

	it('applies a list override', () => {
		const c = { positions: {}, listFamilies: { a: 'droite' as const } };
		expect(score(result({ a: 50, b: 50 }, 100), lists, families, c)).toBeCloseTo(1);
	});

	it('applies a position override, including null (off-axis)', () => {
		expect(
			score(result({ a: 50, b: 50 }, 100), lists, families, {
				positions: { gauche: -2 },
				listFamilies: {}
			})
		).toBeCloseTo(-0.5);
		expect(
			score(result({ a: 50, b: 50 }, 100), lists, families, {
				positions: { gauche: null },
				listFamilies: {}
			})
		).toBeCloseTo(0.5);
	});

	it('returns null (not 0, not NaN) when exprimes is 0', () => {
		expect(score(result({}, 0), lists, families, NO_OVERRIDES)).toBeNull();
	});

	it('ignores unknown list ids and treats a missing list as share 0', () => {
		expect(score(result({ zzz: 10, a: 10 }, 100), lists, families, NO_OVERRIDES)).toBeCloseTo(-0.1);
	});
});

describe('familyShares', () => {
	it('sums shares per family', () => {
		const s = familyShares(result({ a: 30, b: 20 }, 100), lists, NO_OVERRIDES);
		expect(s.gauche).toBeCloseTo(0.3);
		expect(s.droite).toBeCloseTo(0.2);
	});
});


describe('unclassified votes (municipal elections)', () => {
	it('are left out of the base: the score is computed on classified votes only', () => {
		// 30 gauche, 30 droite, 40 non classé : sur la base classée (60), le score vaut 0
		expect(score(result({ a: 30, b: 30, n: 40 }, 100), lists, families, NO_OVERRIDES)).toBeCloseTo(0);
		// 45 gauche, 15 droite, 40 non classé : (-45 + 15) / 60 = -0,5
		expect(score(result({ a: 45, b: 15, n: 40 }, 100), lists, families, NO_OVERRIDES)).toBeCloseTo(-0.5);
	});

	it('gives no score when fewer than 30 % of the votes are classified', () => {
		expect(MIN_CLASSIFIED).toBe(0.3);
		expect(score(result({ a: 10, b: 10, n: 80 }, 100), lists, families, NO_OVERRIDES)).toBeNull();
		// 40 % de voix étiquetées : au-dessus du seuil, l'orientation est calculée sur cette base
		expect(score(result({ a: 30, b: 10, n: 60 }, 100), lists, families, NO_OVERRIDES)).toBeCloseTo(-0.5);
		expect(score(result({ n: 100 }, 100), lists, families, NO_OVERRIDES)).toBeNull();
	});

	it('does not change elections without unclassified votes', () => {
		expect(score(result({ a: 50, c: 50 }, 100), lists, families, NO_OVERRIDES)).toBeCloseTo(-0.5);
	});

	it('reports the classified share', () => {
		expect(classifiedShare(result({ a: 30, b: 30, n: 40 }, 100), lists, families, NO_OVERRIDES)).toBeCloseTo(0.6);
		expect(classifiedShare(result({ a: 50, b: 50 }, 100), lists, families, NO_OVERRIDES)).toBeCloseTo(1);
		expect(classifiedShare(result({}, 0), lists, families, NO_OVERRIDES)).toBe(1);
	});
});
