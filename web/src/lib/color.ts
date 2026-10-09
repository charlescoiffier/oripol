import { interpolateRgb } from 'd3-interpolate';

export const NO_DATA_COLOR = '#d9d9d9';

const LEFT = '#b3261e';
const MIDDLE = '#f2efe6';
const RIGHT = '#1f4e9c';

const toLeft = interpolateRgb(MIDDLE, LEFT);
const toRight = interpolateRgb(MIDDLE, RIGHT);

/** Rouge (gauche) → crème (centre) → bleu (droite), borné à [-2, 2]. */
export function scoreColor(score: number | null): string {
	if (score === null || Number.isNaN(score)) return NO_DATA_COLOR;
	const s = Math.max(-2, Math.min(2, score));
	return s < 0 ? toLeft(-s / 2) : toRight(s / 2);
}
