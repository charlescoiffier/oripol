import { familyShares, score } from './score';
import type { Classification, ElectionData, Family, FamilyId } from './types';

export interface SeriesPoint {
	electionId: string;
	label: string;
	year: number;
	score: number | null;
	shares: Partial<Record<FamilyId, number>>;
	abstention: number | null;
}

export function buildSeries(
	elections: ElectionData[],
	type: string,
	territoryId: string,
	families: Family[],
	c: Classification
): SeriesPoint[] {
	return elections
		.filter((e) => e.type === type && e.territories[territoryId])
		.sort((a, b) => a.year - b.year || a.round - b.round)
		.map((e) => {
			const r = e.territories[territoryId];
			return {
				electionId: e.id,
				label: e.label,
				year: e.year,
				score: score(r, e.lists, families, c),
				shares: familyShares(r, e.lists, c),
				abstention: r.inscrits > 0 ? 1 - r.votants / r.inscrits : null
			};
		});
}
