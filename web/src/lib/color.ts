import { interpolateLab } from 'd3-interpolate';
import { scoreEnds, type PaletteId } from './palette';

/** Gris franc : un territoire sans donnée ne doit jamais ressembler à un territoire « centriste ». */
export const NO_DATA_COLOR = '#8c8c8c';

/** Les scores réels dépassent rarement ±0,6 : la couleur sature à ±SCORE_DOMAIN. */
export const SCORE_DOMAIN = 0.6;

// la couleur monte vite aux faibles écarts : un score national de 0,1 reste nettement coloré
const GAMMA = 0.6;

const scales = new Map<PaletteId, { toLeft: (t: number) => string; toRight: (t: number) => string }>();
function scaleOf(palette: PaletteId) {
	let s = scales.get(palette);
	if (!s) {
		const e = scoreEnds(palette);
		scales.set(palette, (s = { toLeft: interpolateLab(e.middle, e.left), toRight: interpolateLab(e.middle, e.right) }));
	}
	return s;
}

/** Rouge (gauche) → neutre clair (centre) → bleu (droite), borné à [-SCORE_DOMAIN, SCORE_DOMAIN]. */
export function scoreColor(score: number | null, palette: PaletteId = 'standard'): string {
	if (score === null || Number.isNaN(score)) return NO_DATA_COLOR;
	const s = Math.max(-SCORE_DOMAIN, Math.min(SCORE_DOMAIN, score));
	const t = (Math.abs(s) / SCORE_DOMAIN) ** GAMMA;
	const { toLeft, toRight } = scaleOf(palette);
	return s < 0 ? toLeft(t) : toRight(t);
}
