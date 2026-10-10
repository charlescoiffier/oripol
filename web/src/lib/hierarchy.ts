import { levelForId } from './search';
import type { Level } from './types';

const RANK: Record<Level, number> = { pays: 0, regions: 1, departements: 2, communes: 3 };

/** Ancêtre (ou le territoire lui-même) au niveau demandé ; `null` s'il n'en existe pas. */
export function ancestorAt(id: string, level: Level, parents: Record<string, string>): string | null {
	if (level === 'pays') return 'FR';
	let current: string | undefined = id;
	for (let guard = 0; current && guard < 4; guard++) {
		if (levelForId(current) === level) return current;
		current = parents[current];
	}
	return null;
}

export interface LevelChange {
	/** Territoire sélectionné après le changement de niveau (affiché dans le panneau de droite). */
	territory: string | null;
	/** Territoire sur l'emprise duquel zoomer, ou `null` pour ne pas toucher à la vue. */
	focusId: string | null;
}

/**
 * Que devient la sélection quand on change de niveau ?
 * - niveau supérieur : on sélectionne le parent et on zoome dessus ;
 * - niveau inférieur : le territoire reste dans le panneau, on zoome sur son emprise ;
 * - Pays : France entière, vue d'ensemble.
 */
export function planLevelChange(current: string | null, newLevel: Level, parents: Record<string, string>): LevelChange {
	if (newLevel === 'pays' || current === 'FR') return { territory: 'FR', focusId: 'FR' };
	if (!current) return { territory: null, focusId: null };
	const diff = RANK[newLevel] - RANK[levelForId(current)];
	if (diff === 0) return { territory: current, focusId: null };
	if (diff < 0) {
		const ancestor = ancestorAt(current, newLevel, parents);
		return { territory: ancestor ?? current, focusId: ancestor ?? current };
	}
	return { territory: current, focusId: current };
}
