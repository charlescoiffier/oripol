import type { SeriesPoint } from './series';

const nf = new Intl.NumberFormat('fr-FR');
const pf = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const formatCount = (n: number): string => nf.format(n);
/** Part (entre 0 et 1) en pourcentage à la française : « 18,4 % ». */
export const formatPercent = (ratio: number): string => `${pf.format(100 * ratio)} %`;
const percent = (part: number, whole: number): string => `${pf.format((100 * part) / whole)} %`;

/** Lignes d'information d'un scrutin pour un territoire : votants et blancs. */
export function pointDetails(p: SeriesPoint): { votants: string; blancs: string } {
	const votants =
		p.inscrits > 0
			? `Votants : ${formatCount(p.votants)} (${percent(p.votants, p.inscrits)} des inscrits)`
			: `Votants : ${formatCount(p.votants)}`;
	// avant 2017, le fichier source ne sépare pas les blancs des nuls : on ne prétend pas qu'il n'y a aucun blanc
	if (p.blancs === 0 && p.nuls > 0) {
		return { votants, blancs: `Blancs et nuls : ${formatCount(p.nuls)} (non distingués avant 2017)` };
	}
	const blancs =
		p.votants > 0
			? `Blancs : ${formatCount(p.blancs)} (${percent(p.blancs, p.votants)} des votants)`
			: `Blancs : ${formatCount(p.blancs)}`;
	return { votants, blancs };
}
