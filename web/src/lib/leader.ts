import { effectiveFamily } from './score';
import type { Classification, Family, FamilyId, ListInfo, TerritoryResult } from './types';

export interface ResultRow {
	/** Clé de la liste (`<élection>.<nuance>`) : sert au rattachement à une famille. */
	listId: string;
	/** Identifiant unique de la ligne (plusieurs listes peuvent partager une nuance). */
	rowId: string;
	label: string;
	family: FamilyId | undefined;
	/** Candidat, tête de liste ou nom de la liste, quand le fichier source le donne. */
	person?: string;
	voix: number;
	/** Part des suffrages exprimés. */
	share: number;
}

/** Une liste ou un candidat d'une commune, quand le détail existe. */
export interface ListDetail {
	listId: string;
	person: string;
	voix: number;
}

/**
 * Résultats d'un territoire, de la liste la plus votée à la moins votée.
 * Dans une commune, `entries` détaille les listes d'une même nuance ; ailleurs, les voix restent regroupées par nuance
 * (avec le nom de la personne quand elle est unique : `people`).
 */
export function resultRows(
	result: TerritoryResult,
	lists: Record<string, ListInfo>,
	c: Classification,
	people: Record<string, string> = {},
	entries: ListDetail[] = []
): ResultRow[] {
	const detailed = new Map<string, ListDetail[]>();
	for (const e of entries) detailed.set(e.listId, [...(detailed.get(e.listId) ?? []), e]);
	const rows: ResultRow[] = [];
	const share = (voix: number) => (result.exprimes > 0 ? voix / result.exprimes : 0);
	for (const [listId, voix] of Object.entries(result.voix)) {
		if (voix <= 0) continue;
		const base = { listId, label: lists[listId]?.label ?? listId, family: effectiveFamily(listId, lists, c) };
		const parts = detailed.get(listId);
		if (parts) {
			parts.forEach((p, i) => rows.push({ ...base, rowId: `${listId}#${i}`, person: p.person, voix: p.voix, share: share(p.voix) }));
		} else {
			rows.push({ ...base, rowId: listId, person: people[listId], voix, share: share(voix) });
		}
	}
	return rows.sort((a, b) => b.voix - a.voix);
}

/** Liste arrivée en tête parmi les listes classées (les voix sans étiquette ne « gagnent » pas) ; null sans voix classée. */
export function leader(
	result: TerritoryResult,
	lists: Record<string, ListInfo>,
	families: Family[],
	c: Classification,
	entries: ListDetail[] = []
): { listId: string; family: FamilyId } | null {
	const outside = new Set(families.filter((f) => f.inBase === false).map((f) => f.id));
	const best = resultRows(result, lists, c, {}, entries).find((r) => r.family && !outside.has(r.family));
	return best && best.family ? { listId: best.listId, family: best.family } : null;
}
