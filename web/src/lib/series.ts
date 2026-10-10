import { familyShares, score } from './score';
import type { Classification, ElectionData, Family, FamilyId, Precision } from './types';

export interface SeriesPoint {
	electionId: string;
	label: string;
	year: number;
	score: number | null;
	shares: Partial<Record<FamilyId, number>>;
	abstention: number | null;
	/** Blancs + nuls rapportés aux inscrits (avant 2014 les blancs sont comptés dans les nuls). */
	blancsNuls: number | null;
	precision: Precision;
}

export function buildSeries(
	elections: ElectionData[],
	type: string,
	round: number,
	territoryId: string,
	families: Family[],
	c: Classification
): SeriesPoint[] {
	return elections
		.filter((e) => e.type === type && e.round === round && e.territories[territoryId])
		.sort((a, b) => a.year - b.year || a.round - b.round)
		.map((e) => {
			const r = e.territories[territoryId];
			return {
				electionId: e.id,
				label: e.label,
				year: e.year,
				score: score(r, e.lists, families, c),
				shares: familyShares(r, e.lists, c),
				abstention: r.inscrits > 0 ? 1 - r.votants / r.inscrits : null,
				blancsNuls: r.inscrits > 0 ? (r.blancs + r.nuls) / r.inscrits : null,
				precision: r.precision
			};
		});
}
