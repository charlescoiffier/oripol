import { describe, expect, it } from 'vitest';
import { classifiedLine, formatCount, formatPercent, pointDetails } from './format';
import type { SeriesPoint } from './series';

const flat = (s: string) => s.replace(/[  ]/g, ' ');

const point = (over: Partial<SeriesPoint> = {}): SeriesPoint => ({
	electionId: 'pres-2022-1',
	label: 'Présidentielle 2022 – 1er tour',
	year: 2022,
	score: 0.1,
	shares: {},
	abstention: 0.2,
	blancsNuls: 0.02,
	precision: 'commune',
	inscrits: 1000,
	votants: 800,
	blancs: 16,
	nuls: 4,
	classified: 1,
	...over
});

describe('formatCount', () => {
	it('groups thousands in the French way', () => {
		expect(flat(formatCount(1234567))).toBe('1 234 567');
		expect(formatCount(12)).toBe('12');
	});
});

describe('formatPercent', () => {
	it('uses a decimal comma', () => {
		expect(flat(formatPercent(0.1843))).toBe('18,4 %');
	});
});

describe('classifiedLine', () => {
	it('is absent when every vote is classified', () => {
		expect(classifiedLine(point())).toBeNull();
	});
	it('tells how many votes carry a political label otherwise', () => {
		expect(flat(classifiedLine(point({ classified: 0.38 })) ?? '')).toBe('Voix avec étiquette politique : 38,0 %');
	});
});

describe('pointDetails', () => {
	it('gives voters (with turnout) and blank votes (with share of voters)', () => {
		const d = pointDetails(point());
		expect(flat(d.votants)).toBe('Votants : 800 (80,0 % des inscrits)');
		expect(flat(d.blancs)).toBe('Blancs : 16 (2,0 % des votants)');
	});
	it('gives abstentions (inscrits minus votants) with their share of registered voters', () => {
		const d = pointDetails(point());
		expect(flat(d.abstentions)).toBe('Abstentions : 200 (20,0 % des inscrits)');
	});
	it('does not claim zero blanks when the source does not separate them from nuls', () => {
		const d = pointDetails(point({ blancs: 0, nuls: 30 }));
		expect(flat(d.blancs)).toBe('Blancs et nuls : 30 (non distingués avant 2017)');
	});
	it('handles a territory with no voters without dividing by zero', () => {
		const d = pointDetails(point({ inscrits: 0, votants: 0, blancs: 0, nuls: 0 }));
		expect(d.votants).toBe('Votants : 0');
		expect(d.abstentions).toBe('Abstentions : 0');
		expect(d.blancs).toBe('Blancs : 0');
	});
});
