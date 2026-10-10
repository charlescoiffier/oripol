import { describe, expect, it } from 'vitest';
import { ancestorAt, planLevelChange } from './hierarchy';

const parents: Record<string, string> = {
	'COM-49092': 'DEP-49', // Cholet
	'DEP-49': 'REG-52', // Maine-et-Loire → Pays de la Loire
	'COM-97411': 'DEP-974',
	'DEP-974': 'REG-04'
};

describe('ancestorAt', () => {
	it('climbs the hierarchy to the requested level', () => {
		expect(ancestorAt('COM-49092', 'departements', parents)).toBe('DEP-49');
		expect(ancestorAt('COM-49092', 'regions', parents)).toBe('REG-52');
		expect(ancestorAt('COM-49092', 'pays', parents)).toBe('FR');
	});
	it('returns the territory itself when it is already at that level', () => {
		expect(ancestorAt('DEP-49', 'departements', parents)).toBe('DEP-49');
	});
	it('returns null when no ancestor exists at that level', () => {
		expect(ancestorAt('DEP-ZZ', 'regions', parents)).toBeNull();
	});
});

describe('planLevelChange', () => {
	it('going up selects the parent at the new level and zooms on it', () => {
		expect(planLevelChange('COM-49092', 'departements', parents)).toEqual({ territory: 'DEP-49', focusId: 'DEP-49' });
		expect(planLevelChange('COM-49092', 'regions', parents)).toEqual({ territory: 'REG-52', focusId: 'REG-52' });
		expect(planLevelChange('DEP-49', 'regions', parents)).toEqual({ territory: 'REG-52', focusId: 'REG-52' });
	});
	it('going down keeps the territory in the panel and zooms on its extent', () => {
		expect(planLevelChange('DEP-49', 'communes', parents)).toEqual({ territory: 'DEP-49', focusId: 'DEP-49' });
		expect(planLevelChange('REG-52', 'departements', parents)).toEqual({ territory: 'REG-52', focusId: 'REG-52' });
	});
	it('staying on the same level changes nothing and does not zoom', () => {
		expect(planLevelChange('DEP-49', 'departements', parents)).toEqual({ territory: 'DEP-49', focusId: null });
	});
	it('Pays always selects France and zooms out', () => {
		expect(planLevelChange('COM-49092', 'pays', parents)).toEqual({ territory: 'FR', focusId: 'FR' });
		expect(planLevelChange(null, 'pays', parents)).toEqual({ territory: 'FR', focusId: 'FR' });
	});
	it('with France selected, any level zooms back to the whole country', () => {
		expect(planLevelChange('FR', 'departements', parents)).toEqual({ territory: 'FR', focusId: 'FR' });
	});
	it('without a selection there is nothing to select or zoom on', () => {
		expect(planLevelChange(null, 'communes', parents)).toEqual({ territory: null, focusId: null });
	});
	it('keeps the territory when it has no ancestor at the new level', () => {
		expect(planLevelChange('DEP-ZZ', 'regions', parents)).toEqual({ territory: 'DEP-ZZ', focusId: 'DEP-ZZ' });
	});
});
