import type { Classification, Family, FamilyId, ListInfo, TerritoryResult } from './types';

export const NO_OVERRIDES: Classification = { positions: {}, listFamilies: {} };

export function effectiveFamily(
	listId: string,
	lists: Record<string, ListInfo>,
	c: Classification
): FamilyId | undefined {
	return c.listFamilies[listId] ?? lists[listId]?.family;
}

export function positionOf(family: Family, c: Classification): number | null {
	return Object.hasOwn(c.positions, family.id) ? (c.positions[family.id] ?? null) : family.position;
}

export function familyShares(
	result: TerritoryResult,
	lists: Record<string, ListInfo>,
	c: Classification
): Partial<Record<FamilyId, number>> {
	const shares: Partial<Record<FamilyId, number>> = {};
	if (result.exprimes <= 0) return shares;
	for (const [listId, voix] of Object.entries(result.voix)) {
		const family = effectiveFamily(listId, lists, c);
		if (!family) continue;
		shares[family] = (shares[family] ?? 0) + voix / result.exprimes;
	}
	return shares;
}

/** Part minimale de voix étiquetées pour calculer une orientation (sinon : pas de score). */
export const MIN_CLASSIFIED = 0.5;

const inBase = (f: Family) => f.inBase !== false;

/** Voix hors base (non classées) en part des exprimés ; renvoie la part de voix classées. */
export function classifiedShare(
	result: TerritoryResult,
	lists: Record<string, ListInfo>,
	families: Family[],
	c: Classification
): number {
	if (result.exprimes <= 0) return 1;
	const shares = familyShares(result, lists, c);
	let outside = 0;
	for (const f of families) if (!inBase(f)) outside += shares[f.id] ?? 0;
	return 1 - outside;
}

export function score(
	result: TerritoryResult,
	lists: Record<string, ListInfo>,
	families: Family[],
	c: Classification
): number | null {
	if (result.exprimes <= 0) return null;
	const classified = classifiedShare(result, lists, families, c);
	// trop peu de voix étiquetées (petites communes aux municipales) : on ne calcule pas d'orientation
	if (classified < MIN_CLASSIFIED) return null;
	const shares = familyShares(result, lists, c);
	let total = 0;
	for (const family of families) {
		const position = positionOf(family, c);
		if (position === null) continue;
		total += position * (shares[family.id] ?? 0);
	}
	return total / classified;
}
