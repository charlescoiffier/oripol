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

export function score(
	result: TerritoryResult,
	lists: Record<string, ListInfo>,
	families: Family[],
	c: Classification
): number | null {
	if (result.exprimes <= 0) return null;
	const shares = familyShares(result, lists, c);
	let total = 0;
	for (const family of families) {
		const position = positionOf(family, c);
		if (position === null) continue;
		total += position * (shares[family.id] ?? 0);
	}
	return total;
}
