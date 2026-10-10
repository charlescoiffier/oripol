import { effectiveFamily } from './score';
import type { Classification, Family, FamilyId, ListInfo, TerritoryResult } from './types';

export interface ResultRow {
	listId: string;
	label: string;
	family: FamilyId | undefined;
	voix: number;
	/** Part des suffrages exprimés. */
	share: number;
}

/** Liste arrivée en tête parmi les listes classées (les voix sans étiquette ne « gagnent » pas) ; null sans voix classée. */
export function leader(
	result: TerritoryResult,
	lists: Record<string, ListInfo>,
	families: Family[],
	c: Classification
): { listId: string; family: FamilyId } | null {
	const outside = new Set(families.filter((f) => f.inBase === false).map((f) => f.id));
	let best: { listId: string; family: FamilyId; voix: number } | null = null;
	for (const [listId, voix] of Object.entries(result.voix)) {
		const family = effectiveFamily(listId, lists, c);
		if (!family || outside.has(family) || voix <= 0) continue;
		if (!best || voix > best.voix) best = { listId, family, voix };
	}
	return best ? { listId: best.listId, family: best.family } : null;
}

/** Résultats d'un territoire, de la liste la plus votée à la moins votée. */
export function resultRows(result: TerritoryResult, lists: Record<string, ListInfo>, c: Classification): ResultRow[] {
	return Object.entries(result.voix)
		.filter(([, voix]) => voix > 0)
		.map(([listId, voix]) => ({
			listId,
			label: lists[listId]?.label ?? listId,
			family: effectiveFamily(listId, lists, c),
			voix,
			share: result.exprimes > 0 ? voix / result.exprimes : 0
		}))
		.sort((a, b) => b.voix - a.voix);
}
