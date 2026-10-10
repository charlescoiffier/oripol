import { describe, expect, it } from 'vitest';
import type { IndexEntry } from './elections';
import { NO_OVERRIDES } from './score';
import { buildSeries } from './series';
import type { ElectionData, Family } from './types';

const families: Family[] = [
	{ id: 'gauche', label: 'G', position: -1, color: '#000' },
	{ id: 'droite', label: 'D', position: 1, color: '#000' },
	{ id: 'non_classe', label: 'NC', position: null, color: '#ccc', inBase: false }
];
const entry = (id: string, year: number, round = 1): IndexEntry => ({ id, type: 'pres', year, round, label: id });

const result = (voix: Record<string, number>, over: Partial<ElectionData['territories'][string]> = {}) => ({
	inscrits: 200,
	votants: 100,
	blancs: 0,
	nuls: 0,
	exprimes: 100,
	voix,
	precision: 'commune' as const,
	...over
});

/** Élection chargée : les listes A (gauche), B (droite) et N (non classé) existent pour tous les territoires. */
const election = (id: string, year: number, territories: Record<string, ReturnType<typeof result>>): ElectionData => ({
	...entry(id, year),
	lists: {
		[`${id}.A`]: { label: 'A', family: 'gauche' },
		[`${id}.B`]: { label: 'B', family: 'droite' },
		[`${id}.N`]: { label: 'N', family: 'non_classe' }
	},
	territories
});
const v = (id: string, a: number, b: number, n = 0) => ({ [`${id}.A`]: a, [`${id}.B`]: b, [`${id}.N`]: n });

const index = [entry('e2002', 2002), entry('e2007', 2007), entry('e2012', 2012)];

describe('buildSeries', () => {
	const loaded = {
		e2002: election('e2002', 2002, { 'DEP-69': result(v('e2002', 30, 70)) }),
		e2012: election('e2012', 2012, { 'DEP-69': result(v('e2012', 60, 40)) })
	};

	it('keeps every comparable election, in the given order, with a status per election', () => {
		const s = buildSeries(index, loaded, 'DEP-69', families, NO_OVERRIDES);
		expect(s.map((p) => [p.year, p.status])).toEqual([
			[2002, 'ok'],
			[2007, 'loading'], // pas encore chargée
			[2012, 'ok']
		]);
		expect(s[0].score).toBeCloseTo(0.4);
		expect(s[2].score).toBeCloseTo(-0.2);
	});

	it('marks an election where the territory has no result as absent, keeping its date', () => {
		const withEmpty = { ...loaded, e2007: election('e2007', 2007, {}) };
		const s = buildSeries(index, withEmpty, 'DEP-69', families, NO_OVERRIDES);
		expect(s[1]).toMatchObject({ year: 2007, status: 'absent', score: null });
		expect(s[1].votants).toBe(0);
	});

	it('marks a result without a computable orientation as unscored (too few classified votes)', () => {
		const sparse = {
			...loaded,
			e2007: election('e2007', 2007, { 'DEP-69': result(v('e2007', 10, 10, 80)) }) // 20 % étiquetés
		};
		const s = buildSeries(index, sparse, 'DEP-69', families, NO_OVERRIDES);
		expect(s[1].status).toBe('unscored');
		expect(s[1].score).toBeNull();
		expect(s[1].classified).toBeCloseTo(0.2);
		expect(s[1].votants).toBe(100); // les chiffres restent disponibles pour la fenêtre au survol
	});

	it('exposes counts, blancs+nuls rate, precision and abstention for the panel', () => {
		const withCounts = {
			e2002: election('e2002', 2002, { 'DEP-69': result(v('e2002', 30, 70), { blancs: 7, nuls: 3 }) })
		};
		const [p] = buildSeries([entry('e2002', 2002)], withCounts, 'DEP-69', families, NO_OVERRIDES);
		expect([p.inscrits, p.votants, p.blancs, p.nuls]).toEqual([200, 100, 7, 3]);
		expect(p.blancsNuls).toBeCloseTo(0.05);
		expect(p.abstention).toBeCloseTo(0.5);
		expect(p.precision).toBe('commune');
		expect(p.classified).toBe(1);
	});

	it('keeps rounds apart because the caller passes the comparable elections only', () => {
		const first = [entry('e2002', 2002, 1)];
		expect(buildSeries(first, loaded, 'DEP-69', families, NO_OVERRIDES)).toHaveLength(1);
	});
});
