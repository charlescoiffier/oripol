import { interpolateLab } from 'd3-interpolate';

/** Gris franc : un territoire sans donnée ne doit jamais ressembler à un territoire « centriste ». */
export const NO_DATA_COLOR = '#8c8c8c';

/** Les scores réels dépassent rarement ±0,6 : la couleur sature à ±SCORE_DOMAIN. */
export const SCORE_DOMAIN = 0.6;

const LEFT = '#b3261e';
const MIDDLE = '#f3f1ea';
const RIGHT = '#1f4e9c';

// la couleur monte vite aux faibles écarts : un score national de 0,1 reste nettement coloré
const GAMMA = 0.6;

const toLeft = interpolateLab(MIDDLE, LEFT);
const toRight = interpolateLab(MIDDLE, RIGHT);

/** Rouge (gauche) → neutre clair (centre) → bleu (droite), borné à [-SCORE_DOMAIN, SCORE_DOMAIN]. */
export function scoreColor(score: number | null): string {
	if (score === null || Number.isNaN(score)) return NO_DATA_COLOR;
	const s = Math.max(-SCORE_DOMAIN, Math.min(SCORE_DOMAIN, score));
	const t = (Math.abs(s) / SCORE_DOMAIN) ** GAMMA;
	return s < 0 ? toLeft(t) : toRight(t);
}
