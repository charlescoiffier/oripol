import { describe, expect, it } from 'vitest';
import { buildSeries } from './series';
import { NO_OVERRIDES } from './score';
import type { ElectionData, Family } from './types';

const families: Family[] = [
	{ id: 'gauche', label: 'G', position: -1, color: '#000' },
	{ id: 'droite', label: 'D', position: 1, color: '#000' }
];
const mk = (id: string, year: number, territories: ElectionData['territories']): ElectionData => ({
	id,
	type: 'pres',
	year,
	round: 1,
	label: id,
	lists: { [`${id}.A`]: { label: 'A', family: 'gauche' }, [`${id}.B`]: { label: 'B', family: 'droite' } },
	territories
});
const res = (a: number, b: number) => ({
	inscrits: 200, votants: 100, blancs: 0, nuls: 0, exprimes: 100,
	voix: { A: a, B: b }, precision: 'commune' as const
});
const withIds = (id: string, r: ReturnType<typeof res>) => ({ ...r, voix: { [`${id}.A`]: r.voix.A, [`${id}.B`]: r.voix.B } });

describe('buildSeries', () => {
	const elections = [
		mk('pres-2012-1', 2012, { 'DEP-69': withIds('pres-2012-1', res(60, 40)) }),
		mk('pres-2002-1', 2002, { 'DEP-69': withIds('pres-2002-1', res(30, 70)) }),
		mk('pres-2007-1', 2007, {}),
		{ ...mk('leg-2012-1', 2012, { 'DEP-69': withIds('leg-2012-1', res(10, 90)) }), type: 'leg' }
	];

	it('sorts by year, keeps only the requested type, and omits elections without data', () => {
		const s = buildSeries(elections, 'pres', 1, 'DEP-69', families, NO_OVERRIDES);
		expect(s.map((p) => p.year)).toEqual([2002, 2012]);
		expect(s[0].score).toBeCloseTo(0.4);
		expect(s[1].score).toBeCloseTo(-0.2);
	});

	it('exposes blancs+nuls rate and precision for the panel', () => {
		const e = mk('pres-2002-1', 2002, {
			'DEP-69': { ...withIds('pres-2002-1', res(30, 70)), blancs: 10, nuls: 10 }
		});
		const [p] = buildSeries([e], 'pres', 1, 'DEP-69', families, NO_OVERRIDES);
		expect(p.blancsNuls).toBeCloseTo(0.1); // 20 / 200 inscrits
		expect(p.precision).toBe('commune');
	});

	it('keeps first and second rounds in separate series', () => {
		const second = { ...mk('pres-2012-2', 2012, { 'DEP-69': withIds('pres-2012-2', res(55, 45)) }), round: 2 };
		const all = [...elections, second];
		expect(buildSeries(all, 'pres', 2, 'DEP-69', families, NO_OVERRIDES).map((p) => p.electionId)).toEqual(['pres-2012-2']);
		expect(buildSeries(all, 'pres', 1, 'DEP-69', families, NO_OVERRIDES).map((p) => p.year)).toEqual([2002, 2012]);
	});

	it('computes abstention from inscrits and votants', () => {
		const s = buildSeries(elections, 'pres', 1, 'DEP-69', families, NO_OVERRIDES);
		expect(s[0].abstention).toBeCloseTo(0.5);
	});
});
