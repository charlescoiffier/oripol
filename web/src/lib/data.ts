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
	loadPeople: (id: string) => Promise<People>;
}

export type People = Record<string, Record<string, string>>;

/** Fichier compact (table de noms + `[nuance, indice, …]` par territoire) → territoire → liste → nom. */
export function decodePeople(election: string, raw: { names: string[]; t: Record<string, (string | number)[]> }): People {
	const out: People = {};
	for (const [tid, flat] of Object.entries(raw.t)) {
		const row: Record<string, string> = {};
		for (let i = 0; i + 1 < flat.length; i += 2) row[`${election}.${flat[i]}`] = raw.names[flat[i + 1] as number];
		out[tid] = row;
	}
	return out;
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
	const peopleCache = new Map<string, Promise<People>>();
	const loadPeople = (id: string): Promise<People> => {
		let p = peopleCache.get(id);
		if (!p) {
			const entry = index.elections.find((e) => e.id === id);
			p = entry?.people
				? get<{ names: string[]; t: Record<string, (string | number)[]> }>(`people/${id}.json`).then((raw) => decodePeople(id, raw))
				: Promise.resolve({});
			p.catch(() => peopleCache.delete(id));
			peopleCache.set(id, p);
		}
		return p;
	};
	return { index: index.elections, families: classification.families, names, lists: classification.lists, loadElection, loadPeople };
}
