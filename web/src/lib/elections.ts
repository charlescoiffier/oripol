export interface IndexEntry {
	id: string;
	type: string;
	year: number;
	round: number;
	label: string;
	/** Un fichier des candidats ou têtes de liste existe pour cette élection. */
	people?: boolean;
}

export const TYPE_LABELS: Record<string, string> = {
	pres: 'Présidentielles',
	euro: 'Européennes',
	legi: 'Législatives',
	regi: 'Régionales',
	dpmt: 'Départementales (et Cantonales)',
	muni: 'Municipales'
};
/** Entrée du menu des types : les cantonales sont les ancêtres des départementales, même élection. */
export const menuType = (type: string): string => (type === 'cant' ? 'dpmt' : type);

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
	for (const e of index) groups.set(menuType(e.type), [...(groups.get(menuType(e.type)) ?? []), e]);
	return [...groups.entries()]
		.sort(([a], [b]) => rank(a) - rank(b))
		.map(([type, entries]) => ({ type, label: TYPE_LABELS[type] ?? type, entries: entries.sort(chronological) }));
}

/** Élections comparables à celle-ci : même type et même tour, de la plus ancienne à la plus récente. */
export function siblings(index: IndexEntry[], id: string): IndexEntry[] {
	const current = index.find((e) => e.id === id);
	if (!current) return [];
	return index.filter((e) => menuType(e.type) === menuType(current.type) && e.round === current.round).sort(chronological);
}

/** Élection ouverte par défaut : le dernier 1er tour du premier type. */
export function defaultElection(index: IndexEntry[]): string | null {
	const first = groupByType(index)[0];
	const firstRounds = first?.entries.filter((e) => e.round === 1) ?? [];
	return firstRounds.at(-1)?.id ?? first?.entries.at(-1)?.id ?? null;
}

/** Élection ouverte quand on choisit un type : son dernier 1er tour (à défaut, sa dernière élection). */
export function defaultElectionOfType(index: IndexEntry[], type: string): string | null {
	const entries = groupByType(index).find((g) => g.type === type)?.entries ?? [];
	return entries.filter((e) => e.round === 1).at(-1)?.id ?? entries.at(-1)?.id ?? null;
}

/** Libellé sans le type (« 2022 – 1er tour ») : le type est choisi dans un menu séparé. */
export function shortLabel(e: IndexEntry): string {
	return `${e.year} – ${e.round === 1 ? '1er' : '2d'} tour`;
}

/** Élection à ouvrir quand on change de type : même année et même tour si possible, sinon la plus récente. */
export function electionForType(index: IndexEntry[], type: string, currentId: string | null): string | null {
	const current = index.find((e) => e.id === currentId);
	const same = current && index.find((e) => menuType(e.type) === type && e.year === current.year && e.round === current.round);
	return same?.id ?? defaultElectionOfType(index, type);
}
