import { describe, expect, it } from 'vitest';
import { applyPalette, scoreEnds } from './palette';
import { scoreColor } from './color';
import type { Family } from './types';

const fam = (id: string, color: string): Family => ({ id: id as Family['id'], label: id, position: 0, color });

describe('palette', () => {
	it('keeps the family colors in the standard palette', () => {
		const f = [fam('gauche', '#d9534f')];
		expect(applyPalette(f, 'standard')).toEqual(f);
	});
	it('replaces the colors of known families in the colour-blind palette, leaving the others', () => {
		const out = applyPalette([fam('gauche', '#d9534f'), fam('autre', '#123456')], 'daltonien');
		expect(out[0].color).not.toBe('#d9534f');
		expect(out[1].color).toBe('#123456');
	});
	it('gives every family a different colour', () => {
		const ids = ['extreme_gauche', 'gauche', 'centre', 'droite', 'extreme_droite', 'divers', 'regionaliste'];
		const colors = applyPalette(ids.map((i) => fam(i, '#000000')), 'daltonien').map((f) => f.color);
		expect(new Set(colors).size).toBe(ids.length);
	});
	it('uses an orange-to-blue gradient instead of red-to-blue', () => {
		expect(scoreEnds('daltonien').left).not.toBe(scoreEnds('standard').left);
		expect(scoreColor(-1, 'daltonien')).not.toBe(scoreColor(-1, 'standard'));
		expect(scoreColor(null, 'daltonien')).toBe(scoreColor(null, 'standard'));
	});
});
