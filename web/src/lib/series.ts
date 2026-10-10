import type { IndexEntry } from './elections';
import { classifiedShare, familyShares, score } from './score';
import type { Classification, ElectionData, Family, FamilyId, Precision } from './types';

/**
 * - ok : résultat et orientation calculée ;
 * - unscored : résultat sans orientation (trop peu de voix étiquetées) ;
 * - absent : le territoire n'a pas de résultat à ce scrutin (ex. élu dès le premier tour) ;
 * - loading : résultats du scrutin pas encore chargés.
 */
export type PointStatus = 'ok' | 'unscored' | 'absent' | 'loading';

export interface SeriesPoint {
	electionId: string;
	label: string;
	year: number;
	round: number;
	status: PointStatus;
	score: number | null;
	shares: Partial<Record<FamilyId, number>>;
	abstention: number | null;
	/** Blancs + nuls rapportés aux inscrits (avant 2014 les blancs sont comptés dans les nuls). */
	blancsNuls: number | null;
	precision: Precision;
	inscrits: number;
	votants: number;
	blancs: number;
	nuls: number;
	/** Part des exprimés portant une étiquette politique (1 hors municipales). */
	classified: number;
}

/**
 * Série d'un territoire sur les élections comparables (`entries`, de la plus ancienne à la plus récente).
 * Chaque élection garde sa date, même sans résultat : le graphique peut ainsi l'exprimer.
 */
export function buildSeries(
	entries: IndexEntry[],
	loaded: Record<string, ElectionData>,
	territoryId: string,
	families: Family[],
	c: Classification
): SeriesPoint[] {
	return entries.map((entry) => {
		const base = {
			electionId: entry.id,
			label: entry.label,
			year: entry.year,
			round: entry.round,
			score: null,
			shares: {},
			abstention: null,
			blancsNuls: null,
			precision: 'commune' as Precision,
			inscrits: 0,
			votants: 0,
			blancs: 0,
			nuls: 0,
			classified: 1
		};
		const e = loaded[entry.id];
		if (!e) return { ...base, status: 'loading' as const };
		const r = e.territories[territoryId];
		if (!r) return { ...base, status: 'absent' as const };
		const s = score(r, e.lists, families, c);
		return {
			...base,
			status: s === null ? ('unscored' as const) : ('ok' as const),
			score: s,
			shares: familyShares(r, e.lists, c),
			abstention: r.inscrits > 0 ? 1 - r.votants / r.inscrits : null,
			blancsNuls: r.inscrits > 0 ? (r.blancs + r.nuls) / r.inscrits : null,
			precision: r.precision,
			inscrits: r.inscrits,
			votants: r.votants,
			blancs: r.blancs,
			nuls: r.nuls,
			classified: classifiedShare(r, e.lists, families, c)
		};
	});
}
