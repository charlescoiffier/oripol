import { describe, expect, it } from 'vitest';
import { defaultElection, groupByType, siblings, type IndexEntry } from './elections';

const e = (type: string, year: number, round: number): IndexEntry => ({
	id: `${type}-${year}-${round}`,
	type,
	year,
	round,
	label: `${type} ${year} T${round}`
});
const index = [e('legi', 2002, 1), e('pres', 2007, 1), e('pres', 2002, 1), e('pres', 2002, 2), e('legi', 2002, 2), e('pres', 2007, 2)];

describe('groupByType', () => {
	it('orders types (présidentielles first) and elections chronologically, round by round', () => {
		const groups = groupByType(index);
		expect(groups.map((g) => g.type)).toEqual(['pres', 'legi']);
		expect(groups[0].entries.map((x) => x.id)).toEqual(['pres-2002-1', 'pres-2002-2', 'pres-2007-1', 'pres-2007-2']);
		expect(groups[1].label).toBe('Législatives');
	});
	it('puts unknown types last without dropping them', () => {
		const groups = groupByType([...index, e('muni', 2020, 1)]);
		expect(groups.map((g) => g.type)).toEqual(['pres', 'legi', 'muni']);
	});
});

describe('siblings', () => {
	it('returns the elections of the same type and round, oldest first', () => {
		expect(siblings(index, 'pres-2007-1').map((x) => x.id)).toEqual(['pres-2002-1', 'pres-2007-1']);
		expect(siblings(index, 'legi-2002-2').map((x) => x.id)).toEqual(['legi-2002-2']);
	});
	it('returns nothing for an unknown id', () => {
		expect(siblings(index, 'zzz')).toEqual([]);
	});
});

describe('defaultElection', () => {
	it('is the latest first round of the first type', () => {
		expect(defaultElection(index)).toBe('pres-2007-1');
	});
	it('is null for an empty index', () => {
		expect(defaultElection([])).toBeNull();
	});
});
