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
			const body = await get<{ territories: Record<string, TerritoryResult> }>(`elections/${e.id}.json`);
			const lists = Object.fromEntries(
				Object.entries(classification.lists).filter(([id]) => id.startsWith(`${e.id}.`))
			);
			return { ...e, lists, territories: body.territories } satisfies ElectionData;
		})
	);
	return { elections, families: classification.families, names };
}
