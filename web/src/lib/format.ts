import type { SeriesPoint } from './series';

const nf = new Intl.NumberFormat('fr-FR');
const pf = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const formatCount = (n: number): string => nf.format(n);
/** Part (entre 0 et 1) en pourcentage à la française : « 18,4 % ». */
export const formatPercent = (ratio: number): string => `${pf.format(100 * ratio)} %`;
const percent = (part: number, whole: number): string => `${pf.format((100 * part) / whole)} %`;

/** Lignes d'information d'un scrutin pour un territoire : votants, abstentions et blancs. */
export function pointDetails(p: SeriesPoint): { votants: string; abstentions: string; blancs: string } {
	const abstainers = Math.max(0, p.inscrits - p.votants);
	const abstentions =
		p.inscrits > 0
			? `Abstentions : ${formatCount(abstainers)} (${percent(abstainers, p.inscrits)} des inscrits)`
			: `Abstentions : ${formatCount(abstainers)}`;
	const votants =
		p.inscrits > 0
			? `Votants : ${formatCount(p.votants)} (${percent(p.votants, p.inscrits)} des inscrits)`
			: `Votants : ${formatCount(p.votants)}`;
	// avant 2017, le fichier source ne sépare pas les blancs des nuls : on ne prétend pas qu'il n'y a aucun blanc
	if (p.blancs === 0 && p.nuls > 0) {
		return { votants, abstentions, blancs: `Blancs et nuls : ${formatCount(p.nuls)} (non distingués avant 2017)` };
	}
	const blancs =
		p.votants > 0
			? `Blancs : ${formatCount(p.blancs)} (${percent(p.blancs, p.votants)} des votants)`
			: `Blancs : ${formatCount(p.blancs)}`;
	return { votants, abstentions, blancs };
}

/** Ligne d'information sur les voix étiquetées, seulement quand une partie des voix ne l'est pas. */
export function classifiedLine(p: SeriesPoint): string | null {
	return p.classified < 0.9995 ? `Voix avec étiquette politique : ${formatPercent(p.classified)}` : null;
}

/** Nuance d'orientation : gauche, centre gauche, centre, centre droit, droite. */
export function orientationLabel(score: number): string {
	if (score <= -0.6) return 'Gauche';
	if (score <= -0.2) return 'Centre gauche';
	if (score < 0.2) return 'Centre';
	if (score < 0.6) return 'Centre droit';
	return 'Droite';
}

/** Explication d'un point du graphique sans orientation affichable ; `null` pour un résultat normal. */
export function statusLine(p: SeriesPoint): string | null {
	if (p.status === 'absent') {
		return p.round > 1
			? 'Pas de second tour dans ce territoire (élection pliée au premier tour)'
			: 'Pas de résultat pour ce territoire';
	}
	if (p.status === 'unscored') {
		return `Orientation moyenne non calculée : seulement ${formatPercent(p.classified)} des voix ont une étiquette politique`;
	}
	return null;
}
