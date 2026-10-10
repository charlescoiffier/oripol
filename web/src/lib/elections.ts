export interface IndexEntry {
	id: string;
	type: string;
	year: number;
	round: number;
	label: string;
}

export const TYPE_LABELS: Record<string, string> = {
	pres: 'Présidentielles',
	legi: 'Législatives',
	euro: 'Européennes',
	muni: 'Municipales',
	dpmt: 'Départementales',
	cant: 'Cantonales',
	regi: 'Régionales'
};
const TYPE_ORDER = Object.keys(TYPE_LABELS);

const rank = (type: string) => {
	const i = TYPE_ORDER.indexOf(type);
	return i < 0 ? TYPE_ORDER.length : i;
};

const chronological = (a: IndexEntry, b: IndexEntry) => a.year - b.year || a.round - b.round;

export interface ElectionGroup {
	type: string;
	label: string;
	entries: IndexEntry[];
}

/** Élections regroupées par type (présidentielles d'abord), de la plus ancienne à la plus récente. */
export function groupByType(index: IndexEntry[]): ElectionGroup[] {
	const groups = new Map<string, IndexEntry[]>();
	for (const e of index) groups.set(e.type, [...(groups.get(e.type) ?? []), e]);
	return [...groups.entries()]
		.sort(([a], [b]) => rank(a) - rank(b))
		.map(([type, entries]) => ({ type, label: TYPE_LABELS[type] ?? type, entries: entries.sort(chronological) }));
}

/** Élections comparables à celle-ci : même type et même tour, de la plus ancienne à la plus récente. */
export function siblings(index: IndexEntry[], id: string): IndexEntry[] {
	const current = index.find((e) => e.id === id);
	if (!current) return [];
	return index.filter((e) => e.type === current.type && e.round === current.round).sort(chronological);
}

/** Élection ouverte par défaut : le dernier 1er tour du premier type. */
export function defaultElection(index: IndexEntry[]): string | null {
	const first = groupByType(index)[0];
	const firstRounds = first?.entries.filter((e) => e.round === 1) ?? [];
	return firstRounds.at(-1)?.id ?? first?.entries.at(-1)?.id ?? null;
}
