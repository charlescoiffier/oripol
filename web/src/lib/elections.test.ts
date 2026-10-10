import { describe, expect, it } from 'vitest';
import { defaultElection, defaultElectionOfType, electionForType, groupByType, shortLabel, siblings, type IndexEntry } from './elections';

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

describe('defaultElectionOfType', () => {
	it('is the latest first round of that type', () => {
		expect(defaultElectionOfType(index, 'pres')).toBe('pres-2007-1');
		expect(defaultElectionOfType(index, 'legi')).toBe('legi-2002-1');
	});
	it('falls back to the latest election when there is no first round', () => {
		expect(defaultElectionOfType([e('muni', 2020, 2)], 'muni')).toBe('muni-2020-2');
	});
	it('is null for an unknown type', () => {
		expect(defaultElectionOfType(index, 'zzz')).toBeNull();
	});
});

describe('shortLabel', () => {
	it('shows year and round without the type, since the type is chosen separately', () => {
		expect(shortLabel(e('pres', 2022, 1))).toBe('2022 – 1er tour');
		expect(shortLabel(e('legi', 2024, 2))).toBe('2024 – 2d tour');
	});
});

describe('electionForType', () => {
	it('keeps the same year and round when the new type has that election', () => {
		const idx = [e('pres', 2002, 1), e('pres', 2007, 1), e('legi', 2002, 1), e('legi', 2007, 1), e('legi', 2012, 1)];
		expect(electionForType(idx, 'legi', 'pres-2007-1')).toBe('legi-2007-1');
	});
	it('otherwise falls back to the latest first round of the new type', () => {
		const idx = [e('pres', 2022, 1), e('legi', 2002, 1), e('legi', 2007, 1)];
		expect(electionForType(idx, 'legi', 'pres-2022-1')).toBe('legi-2007-1');
	});
	it('works without a current election', () => {
		expect(electionForType(index, 'legi', null)).toBe('legi-2002-1');
	});
});
