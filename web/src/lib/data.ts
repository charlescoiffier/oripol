import type { IndexEntry } from './elections';
import type { ElectionData, Family, ListInfo, TerritoryResult } from './types';

export interface Dataset {
	/** Liste des élections (métadonnées seules : les résultats se chargent à la demande). */
	index: IndexEntry[];
	families: Family[];
	names: Record<string, string>;
	/** Rattachement liste/candidat → famille, toutes élections confondues (clés `<élection>.<liste>`). */
	lists: Record<string, ListInfo>;
	loadElection: (id: string) => Promise<ElectionData>;
	/** Candidats ou têtes de liste par territoire (clés `<élection>.<liste>`), pour les scrutins qui en disposent. */
	loadPeople: (id: string) => Promise<PeopleData>;
}

/** Une liste ou un candidat d'une commune (clé `<élection>.<nuance>`). */
export interface ListEntry {
	listId: string;
	person: string;
	voix: number;
}

export interface PeopleData {
	/** Noms uniques des territoires agrégés (le pays sert de repli). */
	names: Record<string, Record<string, string>>;
	/** Listes des communes, une à une, de la plus votée à la moins votée. */
	lists: Record<string, ListEntry[]>;
}

export const NO_PEOPLE: PeopleData = { names: {}, lists: {} };

type PackedPeople = { names: string[]; t: Record<string, (string | number)[]>; c?: Record<string, (string | number)[]> };

/** Fichier compact (table de noms, `[nuance, nom, …]` et `[nuance, nom, voix, …]`) → noms et listes par territoire. */
export function decodePeople(election: string, raw: PackedPeople): PeopleData {
	const names: PeopleData['names'] = {};
	for (const [tid, flat] of Object.entries(raw.t)) {
		const row: Record<string, string> = {};
		for (let i = 0; i + 1 < flat.length; i += 2) row[`${election}.${flat[i]}`] = raw.names[flat[i + 1] as number];
		names[tid] = row;
	}
	const lists: PeopleData['lists'] = {};
	for (const [tid, flat] of Object.entries(raw.c ?? {})) {
		const row: ListEntry[] = [];
		for (let i = 0; i + 2 < flat.length; i += 3) {
			row.push({ listId: `${election}.${flat[i]}`, person: raw.names[flat[i + 1] as number], voix: flat[i + 2] as number });
		}
		lists[tid] = row;
	}
	return { names, lists };
}

/** Noms connus pour un territoire agrégé : les siens, sinon ceux du pays. */
export function namesFor(p: PeopleData, territoryId: string): Record<string, string> {
	return { ...p.names.FR, ...p.names[territoryId] };
}

export function decodeTerritories(raw: {
	lists: string[];
	territories: Record<string, number[]>;
}): Record<string, TerritoryResult> {
	const out: Record<string, TerritoryResult> = {};
	for (const [id, row] of Object.entries(raw.territories)) {
		const voix: Record<string, number> = {};
		raw.lists.forEach((list, i) => {
			if (row[5 + i] > 0) voix[list] = row[5 + i];
		});
		out[id] = {
			inscrits: row[0],
			votants: row[1],
			blancs: row[2],
			nuls: row[3],
			exprimes: row[4],
			voix,
			precision: 'commune'
		};
	}
	return out;
}

export async function loadDataset(fetchFn: typeof fetch, base: string): Promise<Dataset> {
	const get = async <T>(path: string): Promise<T> => {
		const r = await fetchFn(`${base}/data/${path}`);
		if (!r.ok) throw new Error(`Chargement impossible: ${path} (${r.status})`);
		return r.json() as Promise<T>;
	};
	const [index, classification, names] = await Promise.all([
		get<{ elections: IndexEntry[] }>('index.json'),
		get<{ families: Family[]; lists: Record<string, ListInfo> }>('classification.json'),
		get<Record<string, string>>('names.json')
	]);
	const cache = new Map<string, Promise<ElectionData>>();
	const loadElection = (id: string): Promise<ElectionData> => {
		let p = cache.get(id);
		if (!p) {
			const entry = index.elections.find((e) => e.id === id);
			if (!entry) return Promise.reject(new Error(`Élection inconnue : ${id}`));
			p = get<{ lists: string[]; territories: Record<string, number[]> }>(`elections/${id}.json`).then((body) => {
				const lists = Object.fromEntries(
					Object.entries(classification.lists).filter(([key]) => key.startsWith(`${id}.`))
				);
				return { ...entry, lists, territories: decodeTerritories(body) } satisfies ElectionData;
			});
			p.catch(() => cache.delete(id)); // une erreur réseau n'est pas mise en cache
			cache.set(id, p);
		}
		return p;
	};
	const peopleCache = new Map<string, Promise<PeopleData>>();
	const loadPeople = (id: string): Promise<PeopleData> => {
		let p = peopleCache.get(id);
		if (!p) {
			const entry = index.elections.find((e) => e.id === id);
			p = entry?.people
				? get<PackedPeople>(`people/${id}.json`).then((raw) => decodePeople(id, raw))
				: Promise.resolve(NO_PEOPLE);
			p.catch(() => peopleCache.delete(id));
			peopleCache.set(id, p);
		}
		return p;
	};
	return { index: index.elections, families: classification.families, names, lists: classification.lists, loadElection, loadPeople };
}
