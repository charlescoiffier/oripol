import { describe, expect, it } from 'vitest';
import { fileName } from './export';

describe('fileName', () => {
	it('builds a safe lowercase ASCII name', () => {
		expect(fileName('Présidentielles 2022 – 1er tour', "Côte-d'Or")).toBe('oripol-presidentielles-2022-1er-tour-cote-d-or');
	});
});
