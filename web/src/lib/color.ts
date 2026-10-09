import { interpolateRgb } from 'd3-interpolate';

export const NO_DATA_COLOR = '#b9b9b9';

/** Les scores réels dépassent rarement ±0,6 : la couleur sature à ±SCORE_DOMAIN pour rester lisible. */
export const SCORE_DOMAIN = 0.6;

const LEFT = '#b3261e';
const MIDDLE = '#fbf6e9';
const RIGHT = '#1f4e9c';

const toLeft = interpolateRgb(MIDDLE, LEFT);
const toRight = interpolateRgb(MIDDLE, RIGHT);

/** Rouge (gauche) → crème (centre) → bleu (droite), borné à [-SCORE_DOMAIN, SCORE_DOMAIN]. */
export function scoreColor(score: number | null): string {
	if (score === null || Number.isNaN(score)) return NO_DATA_COLOR;
	const s = Math.max(-SCORE_DOMAIN, Math.min(SCORE_DOMAIN, score));
	return s < 0 ? toLeft(-s / SCORE_DOMAIN) : toRight(s / SCORE_DOMAIN);
}
