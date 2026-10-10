import { describe, expect, it } from 'vitest';
import { displayName, levelForId, searchTerritories } from './search';

const names: Record<string, string> = {
	FR: 'France',
	'REG-84': 'Auvergne-Rhône-Alpes',
	'DEP-69': 'Rhône',
	'COM-69123': 'Lyon',
	'COM-69266': 'Villeurbanne',
	'COM-97101': 'Les Abymes',
	'COM-33063': 'Bordeaux',
	'DEP-ZZ': 'Français établis hors de France'
};

describe('searchTerritories', () => {
	it('returns nothing for an empty query', () => {
		expect(searchTerritories(names, '  ')).toEqual([]);
	});

	it('ignores case, accents and hyphens', () => {
		const ids = searchTerritories(names, 'rhone').map((h) => h.id);
		expect(ids).toContain('DEP-69');
		expect(ids).toContain('REG-84');
	});

	it('ranks prefix matches before inner matches, then by level', () => {
		const ids = searchTerritories(names, 'rhone').map((h) => h.id);
		expect(ids[0]).toBe('DEP-69'); // « Rhône » commence par la requête
	});

	it('labels the level and gives the department for communes', () => {
		const [lyon] = searchTerritories(names, 'lyon');
		expect(lyon).toMatchObject({ id: 'COM-69123', label: 'Lyon (69)', kind: 'Commune' });
		const [abymes] = searchTerritories(names, 'abymes');
		expect(abymes.label).toBe('Les Abymes (971)');
	});

	it('does not change the labels of other levels', () => {
		expect(searchTerritories(names, 'rhône')[0].label).toBe('Rhône');
	});

	it('limits the number of results', () => {
		expect(searchTerritories(names, 'e', 3)).toHaveLength(3);
	});

	it('finds the abroad territory', () => {
		expect(searchTerritories(names, 'etablis')[0].id).toBe('DEP-ZZ');
	});
});

describe('displayName', () => {
	it('adds the department number after the name of a commune only', () => {
		expect(displayName('COM-69123', 'Lyon')).toBe('Lyon (69)');
		expect(displayName('COM-2A004', 'Ajaccio')).toBe('Ajaccio (2A)');
		expect(displayName('COM-97101', 'Les Abymes')).toBe('Les Abymes (971)');
		expect(displayName('DEP-69', 'Rhône')).toBe('Rhône');
		expect(displayName('FR', 'France')).toBe('France');
	});
});

describe('levelForId', () => {
	it('maps a territory id to the map level that shows it', () => {
		expect(levelForId('FR')).toBe('pays');
		expect(levelForId('REG-84')).toBe('regions');
		expect(levelForId('DEP-69')).toBe('departements');
		expect(levelForId('COM-69123')).toBe('communes');
	});

	it('falls back to departements for unknown ids', () => {
		expect(levelForId('???')).toBe('departements');
	});
});
