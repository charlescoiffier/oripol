import type { Level } from './types';

export interface Hit {
	id: string;
	label: string;
	kind: 'Pays' | 'Région' | 'Département' | 'Commune';
	/** Département d'une commune, pour distinguer les homonymes. */
	hint: string;
}

const KINDS: [string, Hit['kind']][] = [
	['FR', 'Pays'],
	['REG-', 'Région'],
	['DEP-', 'Département'],
	['COM-', 'Commune']
];

const normalize = (s: string): string =>
	s
		.normalize('NFD')
		.replace(/\p{M}/gu, '')
		.toLowerCase()
		.replace(/[-'’]/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();

function kindOf(id: string): number {
	return KINDS.findIndex(([prefix]) => id === prefix || id.startsWith(prefix));
}

function departmentOf(id: string): string {
	const code = id.slice(4);
	return /^(97|98)/.test(code) ? code.slice(0, 3) : code.slice(0, 2);
}

export function searchTerritories(names: Record<string, string>, query: string, limit = 30): Hit[] {
	const q = normalize(query);
	if (!q) return [];
	const scored: { hit: Hit; starts: boolean; level: number }[] = [];
	for (const [id, label] of Object.entries(names)) {
		const level = kindOf(id);
		if (level < 0) continue;
		const n = normalize(label);
		const at = n.indexOf(q);
		if (at < 0) continue;
		scored.push({
			hit: {
				id,
				label,
				kind: KINDS[level][1],
				hint: KINDS[level][1] === 'Commune' ? departmentOf(id) : ''
			},
			starts: at === 0,
			level
		});
	}
	scored.sort(
		(a, b) =>
			Number(b.starts) - Number(a.starts) ||
			a.level - b.level ||
			a.hit.label.localeCompare(b.hit.label, 'fr')
	);
	return scored.slice(0, limit).map((s) => s.hit);
}

/** Niveau de carte sur lequel un territoire est affiché. */
export function levelForId(id: string): Level {
	if (id === 'FR') return 'pays';
	if (id.startsWith('REG-')) return 'regions';
	if (id.startsWith('COM-')) return 'communes';
	return 'departements';
}
