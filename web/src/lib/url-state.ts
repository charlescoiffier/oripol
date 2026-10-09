import type { Classification, FamilyId, Level } from './types';

export interface AppState {
	election: string | null;
	territory: string | null;
	level: Level;
	classification: Classification;
}

const LEVELS: ReadonlySet<string> = new Set(['pays', 'regions', 'departements', 'communes']);

export function encodeState(s: AppState): string {
	const q = new URLSearchParams();
	if (s.election) q.set('e', s.election);
	if (s.territory) q.set('t', s.territory);
	if (s.level !== 'departements') q.set('v', s.level);
	const p = Object.entries(s.classification.positions).map(
		([family, pos]) => `${family}~${pos === null ? 'x' : pos}`
	);
	if (p.length) q.set('p', p.join(','));
	const l = Object.entries(s.classification.listFamilies).map(([id, family]) => `${id}~${family}`);
	if (l.length) q.set('l', l.join(','));
	return q.toString();
}

export function decodeState(qs: string, validFamilies: ReadonlySet<string>): AppState {
	const q = new URLSearchParams(qs);
	const level = q.get('v');
	const positions: Classification['positions'] = {};
	for (const entry of (q.get('p') ?? '').split(',')) {
		const [family, raw] = entry.split('~');
		if (!family || raw === undefined || !validFamilies.has(family)) continue;
		if (raw === 'x') {
			positions[family as FamilyId] = null;
			continue;
		}
		const n = Number(raw);
		if (raw.trim() === '' || !Number.isFinite(n)) continue;
		positions[family as FamilyId] = Math.max(-2, Math.min(2, n));
	}
	const listFamilies: Classification['listFamilies'] = {};
	for (const entry of (q.get('l') ?? '').split(',')) {
		const [id, family] = entry.split('~');
		if (!id || !family || !validFamilies.has(family)) continue;
		listFamilies[id] = family as FamilyId;
	}
	return {
		election: q.get('e'),
		territory: q.get('t'),
		level: level && LEVELS.has(level) ? (level as Level) : 'departements',
		classification: { positions, listFamilies }
	};
}
