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
	return { index: index.elections, families: classification.families, names, lists: classification.lists, loadElection };
}
