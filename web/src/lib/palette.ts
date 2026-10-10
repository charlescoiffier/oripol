import type { Family } from './types';

export type PaletteId = 'standard' | 'daltonien';

/** Teintes distinguables par les daltoniens (adaptées d'Okabe-Ito) : brun, orange, jaune, bleu clair, bleu nuit. */
const DALTONIEN: Record<string, string> = {
	extreme_gauche: '#7a3b00',
	gauche: '#e69f00',
	centre: '#f0e442',
	droite: '#56b4e9',
	extreme_droite: '#0b2a5b',
	divers: '#cc79a7',
	regionaliste: '#009e73'
};

/** Familles recolorées selon la palette choisie. */
export function applyPalette(families: Family[], palette: PaletteId): Family[] {
	if (palette === 'standard') return families;
	return families.map((f) => ({ ...f, color: DALTONIEN[f.id] ?? f.color }));
}

/** Extrémités et milieu de l'échelle de l'orientation : rouge → bleu, ou orange → bleu pour les daltoniens. */
export function scoreEnds(palette: PaletteId): { left: string; middle: string; right: string } {
	return {
		left: palette === 'daltonien' ? '#b85c00' : '#b3261e',
		middle: '#f3f1ea',
		right: '#1f4e9c'
	};
}
