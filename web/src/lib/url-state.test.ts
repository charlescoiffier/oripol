import { describe, expect, it } from 'vitest';
import { decodeState, encodeState, type AppState } from './url-state';

const valid = new Set(['extreme_gauche', 'gauche', 'centre', 'droite', 'extreme_droite', 'divers', 'regionaliste']);

const state: AppState = {
	election: 'pres-2022-1',
	territory: 'DEP-69',
	level: 'departements',
	mode: 'classique',
	palette: 'daltonien',
	classification: {
		positions: { gauche: -1.5, divers: null },
		listFamilies: { 'pres-2022-1.LE PEN': 'droite' }
	}
};

describe('url-state', () => {
	it('round-trips a full state', () => {
		expect(decodeState(encodeState(state), valid)).toEqual(state);
	});

	it('uses defaults for an empty query', () => {
		expect(decodeState('', valid)).toEqual({
			election: null,
			territory: null,
			level: 'departements',
			mode: 'evolution',
			palette: 'standard',
			classification: { positions: {}, listFamilies: {} }
		});
	});

	it('ignores unknown families, invalid numbers, unknown levels and malformed pairs', () => {
		const s = decodeState(
			'v=bogus&p=ghost~1,gauche~abc,droite~9,centre&l=pres-2022-1.X~ghost,pres-2022-1.Y~centre',
			valid
		);
		expect(s.level).toBe('departements');
		expect(decodeState('m=zzz&c=zzz', valid)).toMatchObject({ mode: 'evolution', palette: 'standard' });
		expect(s.classification.positions).toEqual({ droite: 2 });
		expect(s.classification.listFamilies).toEqual({ 'pres-2022-1.Y': 'centre' });
	});
});
