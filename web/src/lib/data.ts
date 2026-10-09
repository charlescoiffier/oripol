import type { ElectionData, Family, ListInfo, TerritoryResult } from './types';

export interface Dataset {
	elections: ElectionData[];
	families: Family[];
	names: Record<string, string>;
}

interface IndexEntry {
	id: string;
	type: string;
	year: number;
	round: number;
	label: string;
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
	const elections = await Promise.all(
		index.elections.map(async (e) => {
			const body = await get<{ lists: string[]; territories: Record<string, number[]> }>(
				`elections/${e.id}.json`
			);
			const lists = Object.fromEntries(
				Object.entries(classification.lists).filter(([id]) => id.startsWith(`${e.id}.`))
			);
			return { ...e, lists, territories: decodeTerritories(body) } satisfies ElectionData;
		})
	);
	return { elections, families: classification.families, names };
}
