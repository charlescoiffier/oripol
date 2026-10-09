# Oripol – Socle + présidentielles 2002-2022 : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Livrer un site statique montrant, pour les présidentielles (1er tour) 2002-2022, une carte (régions, départements, communes cibles) colorée par score gauche-droite, une fiche territoire (courbes) et un éditeur de classement dont l'état se partage par URL.

**Architecture:** Un ETL Python (polars) lit les fichiers officiels, résout les fusions de communes, applique une table datée de rattachement candidat → famille, vérifie les totaux, puis exporte des JSON statiques et des contours PMTiles. Un site SvelteKit statique charge ces fichiers et calcule le score côté navigateur (fonction pure `score`), ce qui rend le classement ajustable sans serveur.

**Tech Stack:** Python 3.11+, uv, polars, PyYAML, pytest · SvelteKit (Svelte 5, TypeScript, adapter-static), Vitest, MapLibre GL JS + pmtiles, Apache ECharts, d3-interpolate · tippecanoe (contours).

**Spec:** `docs/superpowers/specs/2026-10-09-oripol-design.md`

## Inconnues connues (à lever à la Task 6, avant toute ligne d'ingestion réelle)
Les noms exacts de colonnes/feuilles des fichiers Insee et du jeu data.gouv « Données des élections agrégées » n'ont pas pu être vérifiés lors du cadrage. Les Tasks 1-5 n'en dépendent pas (elles sont testées sur des données synthétiques). La Task 6 télécharge les vrais fichiers, **vérifie** chaque nom de colonne par un script, et corrige `etl/src/oripol_etl/config.py` si besoin. Ne pas continuer au-delà de la Task 6 tant que `check_config.py` ne passe pas.

## Global Constraints
- Géographie de référence : découpage communal **actuel** ; anciennes communes fusionnées regroupées dans la commune actuelle.
- Familles : `extreme_gauche`(−2), `gauche`(−1), `centre`(0), `droite`(+1), `extreme_droite`(+2), `divers`(hors axe), `regionaliste`(hors axe). EELV et prédécesseurs : `gauche`. Pas de famille « écologistes ».
- Score = Σ (part des suffrages exprimés de la famille × position), familles hors axe exclues du score mais comptées dans les exprimés.
- Une donnée absente n'est jamais interpolée ni affichée comme 0.
- Chaque couple (élection, territoire) porte un champ `precision` (`commune` | `circonscription` | `canton` | `departement`).
- L'ETL échoue (aucun export) si : somme des voix ≠ exprimés, un candidat n'a pas de famille.
- Identifiants de territoire : `FR`, `REG-<code>`, `DEP-<code>`, `COM-<code INSEE actuel>`. Identifiant d'élection : `pres-<année>-<tour>`.
- Identifiant de liste dans l'URL et le classement : `<election_id>.<clé normalisée>` (ex. `pres-2022-1.LE PEN`).
- Pas de serveur applicatif ; hébergement statique ; pas de comptes.

## Review Focus
1. **Arrondissements municipaux** (Paris 751xx, Lyon 6938x, Marseille 132xx) présents dans les fichiers : doivent être agrégés vers 75056 / 69123 / 13055 (Task 4 test).
2. **Code commune réutilisé** : une commune fusionnée puis rétablie ne doit pas être remappée vers l'ancienne commune absorbante (Task 4 test).
3. **Votes des Français établis hors de France** (codes absents du COG, ex. `ZZ`) : ignorés sans planter ; `FR` = France entière hors établis hors de France, à signaler dans l'interface (Task 7 test + Task 12 libellé).
4. **Territoire à 0 exprimé** : score `null`, jamais 0 ni NaN (Task 2 test).
5. **URL partagée corrompue/obsolète** (famille inconnue, nombre invalide, liste d'une autre élection) : ignorée sans erreur (Task 3 test).
6. **Candidat absent d'un territoire** : part 0 pour ce candidat, pas d'erreur (Task 2 test).

## Structure des fichiers
```
.gitignore
etl/pyproject.toml
etl/mappings/presidentielle.yaml          # familles + candidats → famille (données, à valider)
etl/src/oripol_etl/
  __init__.py
  cog.py          # CommuneResolver : anciens codes → commune actuelle
  targets.py      # communes cibles (>30 000 hab. historiques, préfectures, sous-préfectures)
  families.py     # chargement/validation du YAML, normalize_key
  ministry.py     # fichiers « élections agrégées » → tables communales canoniques
  aggregate.py    # communes → payload par territoire (COM/DEP/REG/FR)
  validate.py     # contrôles bloquants
  export.py       # écriture JSON statiques
  config.py       # noms de fichiers/colonnes (vérifiés Task 6)
  pipeline.py     # orchestration
etl/scripts/list_resources.py, download.py, check_config.py, fetch_contours.py
etl/tests/...
web/ (SvelteKit)
  src/lib/types.ts, score.ts, color.ts, url-state.ts, series.ts, data.ts, app-state.svelte.ts
  src/lib/components/Map.svelte, TerritoryPanel.svelte, RankingEditor.svelte
  src/routes/+layout.ts, +page.svelte, sources/+page.svelte, methodologie/+page.svelte
  static/data/ (généré, ignoré par git)
```

---

### Task 1: Squelette du dépôt (ETL + web)

**Files:**
- Create: `.gitignore`, `etl/pyproject.toml`, `etl/src/oripol_etl/__init__.py`, `etl/tests/__init__.py`
- Create: `web/` via `sv create`
- Modify: `web/svelte.config.js`, `web/package.json`
- Create: `web/src/routes/+layout.ts`

**Interfaces:**
- Produces: commandes `cd etl && uv run pytest` et `cd web && npm test` fonctionnelles.

- [ ] **Step 1: Vérifier les outils**

Run: `uv --version && node --version && npm --version`
Expected: trois versions. Si `uv` manque : `brew install uv`.

- [ ] **Step 2: Créer `.gitignore`**

```gitignore
.venv/
__pycache__/
.pytest_cache/
etl/data/
node_modules/
web/.svelte-kit/
web/build/
web/static/data/
.DS_Store
```

- [ ] **Step 3: Créer le projet ETL**

`etl/pyproject.toml` :
```toml
[project]
name = "oripol-etl"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["polars>=1.0", "pyyaml>=6", "httpx>=0.27", "fastexcel>=0.12"]

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/oripol_etl"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```
Créer `etl/src/oripol_etl/__init__.py` et `etl/tests/__init__.py` (vides).

Run: `cd etl && uv sync && uv run pytest`
Expected: « no tests ran » (code de sortie 5, acceptable).

- [ ] **Step 4: Créer le projet SvelteKit**

Run: `npx sv create web --template minimal --types ts --no-add-ons --install npm`
Si les options diffèrent selon la version, lancer `npx sv create web` et choisir : SvelteKit minimal, TypeScript, aucun add-on, npm.

Run: `cd web && npm install -D @sveltejs/adapter-static vitest && npm install maplibre-gl pmtiles echarts d3-interpolate`

- [ ] **Step 5: Configurer le rendu statique**

`web/svelte.config.js` :
```js
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
	preprocess: vitePreprocess(),
	kit: { adapter: adapter({ fallback: 'index.html' }) }
};
```
`web/src/routes/+layout.ts` :
```ts
export const ssr = false;
export const prerender = false;
```
Dans `web/package.json`, ajouter le script `"test": "vitest run"`.

- [ ] **Step 6: Vérifier et committer**

Run: `cd web && npm run build && npm test -- --passWithNoTests`
Expected: build OK ; Vitest sort en code 0.

```bash
git add -A && git commit -m "chore: scaffold etl (uv) and web (sveltekit static)"
```

---

### Task 2: Fonction pure `score` (TDD)

**Files:**
- Create: `web/src/lib/types.ts`, `web/src/lib/score.ts`
- Test: `web/src/lib/score.test.ts`

**Interfaces:**
- Produces (utilisés par les Tasks 3, 10, 11, 12) :
  - `type FamilyId = 'extreme_gauche'|'gauche'|'centre'|'droite'|'extreme_droite'|'divers'|'regionaliste'`
  - `interface Family { id: FamilyId; label: string; position: number | null; color: string }`
  - `interface ListInfo { label: string; family: FamilyId }`
  - `interface TerritoryResult { inscrits:number; votants:number; blancs:number; nuls:number; exprimes:number; voix: Record<string, number>; precision: Precision }`
  - `interface Classification { positions: Partial<Record<FamilyId, number|null>>; listFamilies: Record<string, FamilyId> }`
  - `score(result, lists, families, c): number | null`, `familyShares(result, lists, c)`, `positionOf(family, c)`, `NO_OVERRIDES`
  - Ici `lists` est indexé par **identifiant de liste complet** (`pres-2022-1.LE PEN`) ; `result.voix` utilise la même clé.

- [ ] **Step 1: Écrire `types.ts`**

```ts
export type FamilyId =
	| 'extreme_gauche'
	| 'gauche'
	| 'centre'
	| 'droite'
	| 'extreme_droite'
	| 'divers'
	| 'regionaliste';

export type Precision = 'commune' | 'circonscription' | 'canton' | 'departement';
export type Level = 'regions' | 'departements' | 'communes';

export interface Family {
	id: FamilyId;
	label: string;
	position: number | null;
	color: string;
}

export interface ListInfo {
	label: string;
	family: FamilyId;
}

export interface TerritoryResult {
	inscrits: number;
	votants: number;
	blancs: number;
	nuls: number;
	exprimes: number;
	voix: Record<string, number>;
	precision: Precision;
}

export interface Classification {
	positions: Partial<Record<FamilyId, number | null>>;
	listFamilies: Record<string, FamilyId>;
}

export interface ElectionData {
	id: string;
	type: string;
	year: number;
	round: number;
	label: string;
	lists: Record<string, ListInfo>;
	territories: Record<string, TerritoryResult>;
}
```

- [ ] **Step 2: Écrire le test qui échoue**

`web/src/lib/score.test.ts` :
```ts
import { describe, expect, it } from 'vitest';
import { NO_OVERRIDES, familyShares, score } from './score';
import type { Family, ListInfo, TerritoryResult } from './types';

const families: Family[] = [
	{ id: 'extreme_gauche', label: 'EG', position: -2, color: '#000' },
	{ id: 'gauche', label: 'G', position: -1, color: '#000' },
	{ id: 'centre', label: 'C', position: 0, color: '#000' },
	{ id: 'droite', label: 'D', position: 1, color: '#000' },
	{ id: 'extreme_droite', label: 'ED', position: 2, color: '#000' },
	{ id: 'divers', label: 'Div', position: null, color: '#000' },
	{ id: 'regionaliste', label: 'Reg', position: null, color: '#000' }
];
const lists: Record<string, ListInfo> = {
	a: { label: 'A', family: 'gauche' },
	b: { label: 'B', family: 'droite' },
	c: { label: 'C', family: 'divers' }
};
const result = (voix: Record<string, number>, exprimes: number): TerritoryResult => ({
	inscrits: 200,
	votants: 120,
	blancs: 10,
	nuls: 10,
	exprimes,
	voix,
	precision: 'commune'
});

describe('score', () => {
	it('is 0 when left and right are balanced', () => {
		expect(score(result({ a: 50, b: 50 }, 100), lists, families, NO_OVERRIDES)).toBeCloseTo(0);
	});

	it('dilutes the score with off-axis families but counts them in exprimes', () => {
		expect(score(result({ a: 50, c: 50 }, 100), lists, families, NO_OVERRIDES)).toBeCloseTo(-0.5);
	});

	it('applies a list override', () => {
		const c = { positions: {}, listFamilies: { a: 'droite' as const } };
		expect(score(result({ a: 50, b: 50 }, 100), lists, families, c)).toBeCloseTo(1);
	});

	it('applies a position override, including null (off-axis)', () => {
		expect(
			score(result({ a: 50, b: 50 }, 100), lists, families, {
				positions: { gauche: -2 },
				listFamilies: {}
			})
		).toBeCloseTo(-0.5);
		expect(
			score(result({ a: 50, b: 50 }, 100), lists, families, {
				positions: { gauche: null },
				listFamilies: {}
			})
		).toBeCloseTo(0.5);
	});

	it('returns null (not 0, not NaN) when exprimes is 0', () => {
		expect(score(result({}, 0), lists, families, NO_OVERRIDES)).toBeNull();
	});

	it('ignores unknown list ids and treats a missing list as share 0', () => {
		expect(score(result({ zzz: 10, a: 10 }, 100), lists, families, NO_OVERRIDES)).toBeCloseTo(-0.1);
	});
});

describe('familyShares', () => {
	it('sums shares per family', () => {
		const s = familyShares(result({ a: 30, b: 20 }, 100), lists, NO_OVERRIDES);
		expect(s.gauche).toBeCloseTo(0.3);
		expect(s.droite).toBeCloseTo(0.2);
	});
});
```

- [ ] **Step 3: Vérifier l'échec**

Run: `cd web && npx vitest run src/lib/score.test.ts`
Expected: FAIL (module `./score` introuvable).

- [ ] **Step 4: Implémenter `score.ts`**

```ts
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
```

- [ ] **Step 5: Vérifier le succès et committer**

Run: `cd web && npx vitest run src/lib/score.test.ts`
Expected: PASS (7 tests).

```bash
git add web/src/lib && git commit -m "feat(web): pure score function with overridable classification"
```

---

### Task 3: État dans l'URL et couleur (TDD)

**Files:**
- Create: `web/src/lib/url-state.ts`, `web/src/lib/color.ts`
- Test: `web/src/lib/url-state.test.ts`, `web/src/lib/color.test.ts`

**Interfaces:**
- Consumes: `Classification`, `FamilyId`, `Level` de `types.ts`.
- Produces :
  - `interface AppState { election: string|null; territory: string|null; level: Level; classification: Classification }`
  - `encodeState(s: AppState): string` (sans `?`), `decodeState(qs: string, validFamilies: ReadonlySet<string>): AppState`
  - `scoreColor(score: number | null): string`, `NO_DATA_COLOR`

- [ ] **Step 1: Écrire les tests qui échouent**

`web/src/lib/url-state.test.ts` :
```ts
import { describe, expect, it } from 'vitest';
import { decodeState, encodeState, type AppState } from './url-state';

const valid = new Set(['extreme_gauche', 'gauche', 'centre', 'droite', 'extreme_droite', 'divers', 'regionaliste']);

const state: AppState = {
	election: 'pres-2022-1',
	territory: 'DEP-69',
	level: 'departements',
	classification: {
		positions: { gauche: -1.5, divers: null },
		listFamilies: { 'pres-2022-1.LE PEN': 'droite' }
	}
};

describe('url-state', () => {
	it('round-trips a full state', () => {
		expect(decodeState(encodeState(state), valid)).toEqual(state);
	});

	it('uses defaults for an empty query', () => {
		expect(decodeState('', valid)).toEqual({
			election: null,
			territory: null,
			level: 'departements',
			classification: { positions: {}, listFamilies: {} }
		});
	});

	it('ignores unknown families, invalid numbers, unknown levels and malformed pairs', () => {
		const s = decodeState(
			'v=bogus&p=ghost~1,gauche~abc,droite~9,centre&l=pres-2022-1.X~ghost,pres-2022-1.Y~centre',
			valid
		);
		expect(s.level).toBe('departements');
		expect(s.classification.positions).toEqual({ droite: 2 });
		expect(s.classification.listFamilies).toEqual({ 'pres-2022-1.Y': 'centre' });
	});
});
```
`web/src/lib/color.test.ts` :
```ts
import { describe, expect, it } from 'vitest';
import { NO_DATA_COLOR, scoreColor } from './color';

describe('scoreColor', () => {
	it('returns the no-data color for null', () => {
		expect(scoreColor(null)).toBe(NO_DATA_COLOR);
	});
	it('is darker red at -2 than at -1 and clamps beyond bounds', () => {
		expect(scoreColor(-5)).toBe(scoreColor(-2));
		expect(scoreColor(-2)).not.toBe(scoreColor(-1));
	});
	it('is distinct at both extremes', () => {
		expect(scoreColor(-2)).not.toBe(scoreColor(2));
	});
});
```

- [ ] **Step 2: Vérifier l'échec**

Run: `cd web && npx vitest run`
Expected: FAIL (modules introuvables).

- [ ] **Step 3: Implémenter `url-state.ts`**

```ts
import type { Classification, FamilyId, Level } from './types';

export interface AppState {
	election: string | null;
	territory: string | null;
	level: Level;
	classification: Classification;
}

const LEVELS: ReadonlySet<string> = new Set(['regions', 'departements', 'communes']);

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
```

- [ ] **Step 4: Implémenter `color.ts`**

```ts
import { interpolateRgb } from 'd3-interpolate';

export const NO_DATA_COLOR = '#d9d9d9';

const LEFT = '#b3261e';
const MIDDLE = '#f2efe6';
const RIGHT = '#1f4e9c';

const toLeft = interpolateRgb(MIDDLE, LEFT);
const toRight = interpolateRgb(MIDDLE, RIGHT);

/** Rouge (gauche) → crème (centre) → bleu (droite), borné à [-2, 2]. */
export function scoreColor(score: number | null): string {
	if (score === null || Number.isNaN(score)) return NO_DATA_COLOR;
	const s = Math.max(-2, Math.min(2, score));
	return s < 0 ? toLeft(-s / 2) : toRight(s / 2);
}
```

- [ ] **Step 5: Vérifier et committer**

Run: `cd web && npx vitest run`
Expected: PASS (tous les tests).

```bash
git add web/src/lib && git commit -m "feat(web): url state codec and score color scale"
```

---

### Task 4: Résolution des fusions de communes (TDD)

**Files:**
- Create: `etl/src/oripol_etl/cog.py`
- Test: `etl/tests/test_cog.py`

**Interfaces:**
- Produces (Tasks 5, 7) :
  - `class CommuneResolver` : `resolve(code: str) -> str`, `is_current(code: str) -> bool`
  - `build_resolver(mouvements: pl.DataFrame, current_codes: set[str]) -> CommuneResolver`
  - `mouvements` : colonnes (insensibles à la casse) `mod, date_eff, typecom_av, com_av, typecom_ap, com_ap`.

- [ ] **Step 1: Écrire le test qui échoue**

```python
import polars as pl

from oripol_etl.cog import build_resolver


def mouvements(rows):
    return pl.DataFrame(
        rows,
        schema={
            "MOD": pl.Int64,
            "DATE_EFF": pl.String,
            "TYPECOM_AV": pl.String,
            "COM_AV": pl.String,
            "TYPECOM_AP": pl.String,
            "COM_AP": pl.String,
        },
        orient="row",
    )


def test_simple_merge_maps_old_code_to_new():
    m = mouvements([(31, "2016-01-01", "COM", "11111", "COM", "22222")])
    r = build_resolver(m, {"22222"})
    assert r.resolve("11111") == "22222"
    assert r.resolve("22222") == "22222"


def test_chain_of_merges_resolves_to_final_commune():
    m = mouvements(
        [
            (31, "2010-01-01", "COM", "11111", "COM", "22222"),
            (32, "2019-01-01", "COM", "22222", "COM", "33333"),
        ]
    )
    r = build_resolver(m, {"33333"})
    assert r.resolve("11111") == "33333"


def test_restored_commune_is_not_remapped():
    m = mouvements(
        [
            (31, "2000-01-01", "COM", "11111", "COM", "22222"),
            (21, "2010-01-01", "COM", "22222", "COM", "11111"),
        ]
    )
    r = build_resolver(m, {"11111", "22222"})
    assert r.resolve("11111") == "11111"
    assert r.is_current("11111")


def test_municipal_arrondissements_resolve_to_city():
    r = build_resolver(mouvements([]), {"75056", "69123", "13055"})
    assert r.resolve("75108") == "75056"
    assert r.resolve("69383") == "69123"
    assert r.resolve("13208") == "13055"


def test_unknown_code_is_returned_unchanged_and_not_current():
    r = build_resolver(mouvements([]), {"22222"})
    assert r.resolve("99999") == "99999"
    assert not r.is_current("99999")


def test_cycle_does_not_loop_forever():
    m = mouvements(
        [
            (31, "2000-01-01", "COM", "11111", "COM", "22222"),
            (31, "2001-01-01", "COM", "22222", "COM", "11111"),
        ]
    )
    r = build_resolver(m, set())
    assert r.resolve("11111") in {"11111", "22222"}
```

- [ ] **Step 2: Vérifier l'échec**

Run: `cd etl && uv run pytest tests/test_cog.py -v`
Expected: FAIL (`ModuleNotFoundError: oripol_etl.cog`).

- [ ] **Step 3: Implémenter `cog.py`**

```python
from __future__ import annotations

import polars as pl

ARRONDISSEMENTS_MUNICIPAUX: dict[str, str] = {
    **{f"751{n:02d}": "75056" for n in range(1, 21)},
    **{f"6938{n}": "69123" for n in range(1, 10)},
    **{f"132{n:02d}": "13055" for n in range(1, 17)},
}

# 31 fusion simple, 32 création de commune nouvelle, 33 fusion avec association,
# 34 fusion association → simple, 41 changement de département, 50 changement de code (fusion)
MERGE_MODS = {31, 32, 33, 34, 41, 50}


class CommuneResolver:
    def __init__(self, direct: dict[str, str], current: set[str]):
        self._direct = direct
        self._current = current

    def resolve(self, code: str) -> str:
        code = ARRONDISSEMENTS_MUNICIPAUX.get(code, code)
        seen: set[str] = set()
        while code in self._direct and code not in seen:
            seen.add(code)
            code = self._direct[code]
        return code

    def is_current(self, code: str) -> bool:
        return code in self._current


def build_resolver(mouvements: pl.DataFrame, current_codes: set[str]) -> CommuneResolver:
    df = mouvements.rename({c: c.lower() for c in mouvements.columns})
    df = df.filter(
        pl.col("mod").is_in(list(MERGE_MODS))
        & (pl.col("typecom_av") == "COM")
        & (pl.col("typecom_ap") == "COM")
        & (pl.col("com_av") != pl.col("com_ap"))
    ).sort("date_eff")
    direct: dict[str, str] = {}
    for old, new in zip(df["com_av"], df["com_ap"]):
        if old in current_codes:
            continue  # code réutilisé (commune rétablie) : ne jamais le remapper
        direct[old] = new
    return CommuneResolver(direct, set(current_codes))
```

- [ ] **Step 4: Vérifier et committer**

Run: `cd etl && uv run pytest tests/test_cog.py -v`
Expected: PASS (6 tests).

```bash
git add etl && git commit -m "feat(etl): commune merge resolver with arrondissement and reuse handling"
```

---

### Task 5: Communes cibles (TDD)

**Files:**
- Create: `etl/src/oripol_etl/targets.py`
- Test: `etl/tests/test_targets.py`

**Interfaces:**
- Consumes: `CommuneResolver` (Task 4).
- Produces (Tasks 7, 8, 9) :
  - `population_max(df: pl.DataFrame, id_col: str, exclude: list[str]) -> pl.DataFrame` → colonnes `code, max_population`
  - `chefs_lieux(departements: pl.DataFrame, arrondissements: pl.DataFrame) -> pl.DataFrame` → colonnes `code, motif` (`prefecture`|`sous_prefecture`) ; entrées avec colonnes minuscules `dep, cheflieu` / `arr, cheflieu`
  - `select_targets(max_pop, lieux, resolver, threshold=30000) -> pl.DataFrame` → colonnes `code, motifs` (liste triée jointe par `,`), triée par `code`.

- [ ] **Step 1: Écrire le test qui échoue**

```python
import polars as pl

from oripol_etl.cog import build_resolver
from oripol_etl.targets import chefs_lieux, population_max, select_targets


def empty_resolver(current):
    m = pl.DataFrame(
        schema={
            "MOD": pl.Int64, "DATE_EFF": pl.String, "TYPECOM_AV": pl.String,
            "COM_AV": pl.String, "TYPECOM_AP": pl.String, "COM_AP": pl.String,
        }
    )
    return build_resolver(m, current)


def test_population_max_takes_max_over_numeric_columns_excluding_ids():
    df = pl.DataFrame(
        {"CODGEO": ["A", "B"], "REG": [11, 11], "P1900": [10, 40000.0], "P2020": [35000.0, 100.0]}
    )
    out = population_max(df, "CODGEO", ["REG"]).sort("code")
    assert out["code"].to_list() == ["A", "B"]
    assert out["max_population"].to_list() == [35000.0, 40000.0]


def test_chefs_lieux_distinguishes_prefecture_from_sous_prefecture():
    deps = pl.DataFrame({"dep": ["01"], "cheflieu": ["01053"]})
    arrs = pl.DataFrame({"arr": ["011", "012"], "cheflieu": ["01053", "01004"]})
    out = chefs_lieux(deps, arrs).sort("code")
    assert out.to_dicts() == [
        {"code": "01004", "motif": "sous_prefecture"},
        {"code": "01053", "motif": "prefecture"},
    ]


def test_select_targets_unions_and_resolves_codes():
    max_pop = pl.DataFrame({"code": ["01053", "99999", "11111"], "max_population": [40000.0, 5000.0, 31000.0]})
    lieux = pl.DataFrame({"code": ["01053", "01004"], "motif": ["prefecture", "sous_prefecture"]})
    resolver = empty_resolver({"01053", "01004", "99999", "22222"})
    # 11111 a fusionné dans 22222 : la population doit être rattachée à 22222
    from oripol_etl.cog import CommuneResolver
    resolver = CommuneResolver({"11111": "22222"}, {"01053", "01004", "99999", "22222"})
    out = select_targets(max_pop, lieux, resolver)
    assert out.sort("code").to_dicts() == [
        {"code": "01004", "motifs": "sous_prefecture"},
        {"code": "01053", "motifs": "prefecture,seuil_30000"},
        {"code": "22222", "motifs": "seuil_30000"},
    ]
```

- [ ] **Step 2: Vérifier l'échec**

Run: `cd etl && uv run pytest tests/test_targets.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implémenter `targets.py`**

```python
from __future__ import annotations

import polars as pl

from .cog import CommuneResolver


def population_max(df: pl.DataFrame, id_col: str, exclude: list[str]) -> pl.DataFrame:
    skip = {id_col, *exclude}
    numeric = [c for c in df.columns if c not in skip and df[c].dtype.is_numeric()]
    return df.select(
        pl.col(id_col).alias("code"),
        pl.max_horizontal([pl.col(c) for c in numeric]).alias("max_population"),
    )


def chefs_lieux(departements: pl.DataFrame, arrondissements: pl.DataFrame) -> pl.DataFrame:
    prefectures = departements.select(pl.col("cheflieu").alias("code")).unique()
    prefectures = prefectures.with_columns(pl.lit("prefecture").alias("motif"))
    sous = (
        arrondissements.select(pl.col("cheflieu").alias("code"))
        .unique()
        .join(prefectures.select("code"), on="code", how="anti")
        .with_columns(pl.lit("sous_prefecture").alias("motif"))
    )
    return pl.concat([prefectures, sous])


def select_targets(
    max_pop: pl.DataFrame,
    lieux: pl.DataFrame,
    resolver: CommuneResolver,
    threshold: int = 30000,
) -> pl.DataFrame:
    rows: list[tuple[str, str]] = []
    for code, pop in zip(max_pop["code"], max_pop["max_population"]):
        if pop is not None and pop >= threshold:
            rows.append((resolver.resolve(code), "seuil_30000"))
    for code, motif in zip(lieux["code"], lieux["motif"]):
        rows.append((resolver.resolve(code), motif))
    df = pl.DataFrame(rows, schema={"code": pl.String, "motif": pl.String}, orient="row")
    return (
        df.group_by("code")
        .agg(pl.col("motif").unique().sort().str.join(",").alias("motifs"))
        .sort("code")
    )
```

- [ ] **Step 4: Vérifier et committer**

Run: `cd etl && uv run pytest tests/test_targets.py -v`
Expected: PASS (3 tests).

```bash
git add etl && git commit -m "feat(etl): target commune selection (30k threshold, prefectures)"
```

---

### Task 6: Récupération des sources réelles et vérification de la configuration (GATE)

**Files:**
- Create: `etl/scripts/list_resources.py`, `etl/scripts/download.py`, `etl/scripts/check_config.py`, `etl/src/oripol_etl/config.py`

**Interfaces:**
- Produces (Tasks 7-9) : `config.py` exposant `RAW`, `OUT`, `MAPPING`, `COG_*`, `POP_*`, `GENERAL_FILE`, `CANDIDATES_FILE`, `COLUMNS` (un `ColumnMap`, défini Task 7). Cette task est écrite avant la Task 7 mais `config.py` importe `ColumnMap` : exécuter **Step 5 après la Task 7**, ou créer d'abord la dataclass (Step 5 contient le rappel).

⚠️ Les téléchargements sont des fichiers de sources publiques officielles ; demander la validation de l'utilisateur avant d'exécuter les Steps 2-3 (nom, source, taille sont affichés par `list_resources.py`).

- [ ] **Step 1: Écrire `list_resources.py`**

```python
"""Liste les ressources d'un jeu data.gouv.fr : python list_resources.py <slug>"""
import sys

import httpx

slug = sys.argv[1]
data = httpx.get(f"https://www.data.gouv.fr/api/1/datasets/{slug}/", follow_redirects=True, timeout=60).json()
print(data["title"], "-", data.get("last_modified"))
for r in data["resources"]:
    print(f"- {r['title']} | {r.get('format')} | {r.get('filesize')} o | {r['url']}")
```

- [ ] **Step 2: Lister les ressources utiles**

Run (depuis `etl/`) :
```bash
uv run python scripts/list_resources.py donnees-des-elections-agregees
```
Expected: liste des fichiers (résultats généraux + candidats par bureau). Noter les deux URLs. Si le slug diffère, utiliser l'identifiant `6481e741d4cf002ec0efec9d` à la place du slug.

- [ ] **Step 3: Écrire `download.py` et télécharger**

```python
"""python download.py <url> <destination>"""
import sys
from pathlib import Path

import httpx

url, dest = sys.argv[1], Path(sys.argv[2])
dest.parent.mkdir(parents=True, exist_ok=True)
with httpx.stream("GET", url, follow_redirects=True, timeout=None) as r, dest.open("wb") as f:
    r.raise_for_status()
    for chunk in r.iter_bytes():
        f.write(chunk)
print("OK", dest, dest.stat().st_size)
```
Télécharger dans `etl/data/raw/` : les deux tables élections agrégées ; les fichiers COG Insee (`v_commune_*.csv`, `v_departement_*.csv`, `v_arrondissement_*.csv`, `v_mvt_commune_*.csv`, depuis la page Insee « Code officiel géographique ») ; le fichier « Historique des populations communales 1876-2023 » (xlsx).

- [ ] **Step 4: Inspecter les en-têtes réels**

Run (depuis `etl/`) :
```bash
uv run python -c "
import polars as pl, sys
for p in sys.argv[1:]:
    df = pl.read_parquet(p) if p.endswith('.parquet') else pl.read_csv(p, infer_schema_length=2000)
    print(p, df.shape); print(df.head(3)); print(df.columns)
" data/raw/<table_generale> data/raw/<table_candidats> data/raw/<v_commune>
```
Pour l'xlsx : `uv run python -c "import polars as pl; print(pl.read_excel('data/raw/<pop>.xlsx', sheet_id=0, read_options={'header_row': 0}).head(8))"` et repérer la feuille et la ligne d'en-tête.

- [ ] **Step 5: Écrire `config.py` avec les noms observés**

Valeurs par défaut ci-dessous = hypothèses de cadrage ; **remplacer par ce que Step 4 a montré**. `ColumnMap` est défini Task 7 (`from .ministry import ColumnMap`) : exécuter ce step après la Task 7.

```python
from pathlib import Path

import polars as pl

from .ministry import ColumnMap

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT.parent / "web" / "static" / "data"
MAPPING = ROOT / "mappings" / "presidentielle.yaml"

# --- COG Insee (colonnes lues en minuscules) ---
COG_COMMUNES = RAW / "v_commune.csv"          # colonnes: typecom, com, dep, reg
COG_DEPARTEMENTS = RAW / "v_departement.csv"  # colonnes: dep, cheflieu
COG_ARRONDISSEMENTS = RAW / "v_arrondissement.csv"  # colonnes: arr, cheflieu
COG_MOUVEMENTS = RAW / "v_mvt_commune.csv"    # colonnes: mod, date_eff, typecom_av, com_av, typecom_ap, com_ap

# --- Populations historiques Insee ---
POP_FILE = RAW / "base-pop-historiques-1876-2023.xlsx"
POP_SHEET = "pop_1876_2023"
POP_HEADER_ROW = 4
POP_ID_COL = "CODGEO"
POP_EXCLUDE = ["REG", "DEP"]

# --- Élections agrégées (data.gouv.fr) ---
GENERAL_FILE = RAW / "general_results.parquet"
CANDIDATES_FILE = RAW / "candidats_results.parquet"
COLUMNS = ColumnMap(
    election_id="id_election",
    bureau_id="id_brut_miom",
    commune_code=pl.col("id_brut_miom").str.split("_").list.first(),
    inscrits="inscrits",
    votants="votants",
    blancs="blancs",
    nuls="nuls",
    exprimes="exprimes",
    cand_election_id="id_election",
    cand_bureau_id="id_brut_miom",
    cand_name="nom",
    cand_votes="voix",
)
```

- [ ] **Step 6: Écrire `check_config.py` (échoue si une colonne manque)**

```python
"""Vérifie que chaque fichier/colonne référencé par config.py existe vraiment."""
import polars as pl

from oripol_etl import config as c


def read(path):
    return pl.read_parquet(path) if str(path).endswith(".parquet") else pl.read_csv(path, infer_schema_length=5000)


def need(df, cols, label):
    cols_l = {x.lower() for x in df.columns}
    missing = [x for x in cols if x.lower() not in cols_l]
    assert not missing, f"{label}: colonnes manquantes {missing}; présentes: {df.columns}"
    print("OK", label)


need(read(c.COG_COMMUNES), ["typecom", "com", "dep", "reg"], "COG communes")
need(read(c.COG_DEPARTEMENTS), ["dep", "cheflieu"], "COG départements")
need(read(c.COG_ARRONDISSEMENTS), ["arr", "cheflieu"], "COG arrondissements")
need(read(c.COG_MOUVEMENTS), ["mod", "date_eff", "typecom_av", "com_av", "typecom_ap", "com_ap"], "COG mouvements")
pop = pl.read_excel(c.POP_FILE, sheet_name=c.POP_SHEET, read_options={"header_row": c.POP_HEADER_ROW})
need(pop, [c.POP_ID_COL, *c.POP_EXCLUDE], "Population")
g, k = read(c.GENERAL_FILE), read(c.CANDIDATES_FILE)
cm = c.COLUMNS
need(g, [cm.election_id, cm.bureau_id, cm.inscrits, cm.votants, cm.blancs, cm.nuls, cm.exprimes], "Général")
need(k, [cm.cand_election_id, cm.cand_bureau_id, cm.cand_name, cm.cand_votes], "Candidats")
code = g.select(cm.commune_code.alias("c")).head(5)["c"].to_list()
print("Exemples de code commune:", code)
ids = g[cm.election_id].unique().sort().to_list()
print("id_election exemples:", [i for i in ids if "pres" in str(i)][:12])
```
Run: `cd etl && uv run python scripts/check_config.py`
Expected: lignes `OK` pour chaque bloc, un exemple de code commune à 5 caractères, et des identifiants du type `2022_pres_t1`. **Toute erreur ici se corrige dans `config.py`, pas ailleurs.** Si le format d'`id_election` diffère de `AAAA_pres_tN`, adapter `election_id_from_source` (Task 7).

- [ ] **Step 7: Committer**

```bash
git add etl && git commit -m "feat(etl): source download scripts and verified config"
```

---

### Task 7: Familles, candidats et ingestion des fichiers ministère (TDD)

**Files:**
- Create: `etl/src/oripol_etl/families.py`, `etl/src/oripol_etl/ministry.py`, `etl/mappings/presidentielle.yaml`
- Test: `etl/tests/test_families.py`, `etl/tests/test_ministry.py`

**Interfaces:**
- Consumes: `CommuneResolver` (Task 4).
- Produces (Tasks 8-9) :
  - `normalize_key(s: str) -> str`
  - `@dataclass Family(id, label, position: float|None, color)`, `@dataclass ListMapping(key, label, family, to_validate: bool)`
  - `load_families(path) -> list[Family]`, `load_list_mappings(path) -> dict[str, dict[str, ListMapping]]` (élection → clé → mapping)
  - `@dataclass ColumnMap(election_id, bureau_id, commune_code: pl.Expr, inscrits, votants, blancs, nuls, exprimes, cand_election_id, cand_bureau_id, cand_name, cand_votes)`
  - `election_id_from_source(source_id: str) -> str | None` (`"2022_pres_t1"` → `"pres-2022-1"`, autres → `None`)
  - `to_commune_tables(general, candidates, cm, resolver) -> tuple[pl.DataFrame, pl.DataFrame]` :
    participation `(election_id, code, inscrits, votants, blancs, nuls, exprimes)`, votes `(election_id, code, list_key, voix)`. Seules les élections présidentielles de 1er tour sont conservées ; les codes absents du COG sont conservés tels quels (filtrés plus tard par jointure sur la géographie).

- [ ] **Step 1: Écrire les tests qui échouent**

`etl/tests/test_families.py` :
```python
from pathlib import Path

from oripol_etl.families import load_families, load_list_mappings, normalize_key

MAPPING = Path(__file__).resolve().parents[1] / "mappings" / "presidentielle.yaml"


def test_normalize_key_strips_accents_hyphens_and_case():
    assert normalize_key("Mélenchon") == "MELENCHON"
    assert normalize_key("Dupont-Aignan") == "DUPONT AIGNAN"
    assert normalize_key("  le  pen ") == "LE PEN"


def test_real_mapping_is_consistent():
    families = {f.id for f in load_families(MAPPING)}
    assert families == {
        "extreme_gauche", "gauche", "centre", "droite", "extreme_droite", "divers", "regionaliste"
    }
    mappings = load_list_mappings(MAPPING)
    assert set(mappings) == {"pres-2002-1", "pres-2007-1", "pres-2012-1", "pres-2017-1", "pres-2022-1"}
    for election, lists in mappings.items():
        for key, m in lists.items():
            assert m.family in families, (election, key)
            assert key == normalize_key(key)


def test_known_candidates_counts():
    mappings = load_list_mappings(MAPPING)
    assert len(mappings["pres-2002-1"]) == 16
    assert len(mappings["pres-2007-1"]) == 12
    assert len(mappings["pres-2012-1"]) == 10
    assert len(mappings["pres-2017-1"]) == 11
    assert len(mappings["pres-2022-1"]) == 12


def test_eelv_candidates_are_left():
    m = load_list_mappings(MAPPING)
    assert m["pres-2022-1"]["JADOT"].family == "gauche"
    assert m["pres-2012-1"]["JOLY"].family == "gauche"
```

`etl/tests/test_ministry.py` :
```python
import polars as pl

from oripol_etl.cog import CommuneResolver
from oripol_etl.ministry import ColumnMap, election_id_from_source, to_commune_tables

CM = ColumnMap(
    election_id="id_election",
    bureau_id="bv",
    commune_code=pl.col("code_commune"),
    inscrits="inscrits",
    votants="votants",
    blancs="blancs",
    nuls="nuls",
    exprimes="exprimes",
    cand_election_id="id_election",
    cand_bureau_id="bv",
    cand_name="nom",
    cand_votes="voix",
)


def test_election_id_from_source():
    assert election_id_from_source("2022_pres_t1") == "pres-2022-1"
    assert election_id_from_source("2022_pres_t2") is None
    assert election_id_from_source("2022_legi_t1") is None


def general():
    return pl.DataFrame(
        {
            "id_election": ["2022_pres_t1"] * 4 + ["2022_pres_t2"],
            "bv": ["b1", "b2", "b3", "b4", "b5"],
            "code_commune": ["11111", "22222", "75108", "ZZ", "11111"],
            "inscrits": [100, 50, 200, 10, 100],
            "votants": [80, 40, 150, 5, 80],
            "blancs": [2, 1, 5, 0, 2],
            "nuls": [1, 1, 3, 0, 1],
            "exprimes": [77, 38, 142, 5, 77],
        }
    )


def candidates():
    return pl.DataFrame(
        {
            "id_election": ["2022_pres_t1"] * 8 + ["2022_pres_t2"],
            "bv": ["b1", "b1", "b2", "b2", "b3", "b3", "b4", "b4", "b5"],
            "nom": ["Macron", "Le Pen", "Macron", "Le Pen", "Macron", "Mélenchon", "Macron", "Le Pen", "Macron"],
            "voix": [40, 37, 20, 18, 100, 42, 3, 2, 77],
        }
    )


def test_aggregates_bureaux_to_resolved_communes_and_keeps_only_first_rounds():
    resolver = CommuneResolver({"11111": "22222"}, {"22222", "75056"})
    part, votes = to_commune_tables(general(), candidates(), CM, resolver)

    p = part.filter(pl.col("code") == "22222").to_dicts()[0]
    assert p["election_id"] == "pres-2022-1"
    assert (p["inscrits"], p["exprimes"]) == (150, 115)  # b1 + b2 fusionnées

    assert part.filter(pl.col("code") == "75056")["exprimes"].item() == 142  # arrondissement → Paris
    assert part.filter(pl.col("election_id") != "pres-2022-1").height == 0

    v = votes.filter((pl.col("code") == "22222") & (pl.col("list_key") == "MACRON"))
    assert v["voix"].item() == 60
    assert votes.filter(pl.col("list_key") == "MELENCHON")["voix"].item() == 42


def test_codes_outside_cog_are_kept_untouched_for_later_filtering():
    resolver = CommuneResolver({}, {"22222"})
    part, _ = to_commune_tables(general(), candidates(), CM, resolver)
    assert "ZZ" in part["code"].to_list()
```

- [ ] **Step 2: Vérifier l'échec**

Run: `cd etl && uv run pytest tests/test_ministry.py tests/test_families.py -v`
Expected: FAIL (modules ou fichier YAML manquants).

- [ ] **Step 3: Implémenter `families.py`**

```python
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml


def normalize_key(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[-'’]", " ", s)
    return re.sub(r"\s+", " ", s).strip().upper()


@dataclass(frozen=True)
class Family:
    id: str
    label: str
    position: float | None
    color: str


@dataclass(frozen=True)
class ListMapping:
    key: str
    label: str
    family: str
    to_validate: bool = False


def _read(path: Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_families(path: Path) -> list[Family]:
    return [
        Family(f["id"], f["label"], f.get("position"), f["color"])
        for f in _read(path)["families"]
    ]


def load_list_mappings(path: Path) -> dict[str, dict[str, ListMapping]]:
    data = _read(path)
    known = {f["id"] for f in data["families"]}
    out: dict[str, dict[str, ListMapping]] = {}
    for election_id, entries in data["elections"].items():
        out[election_id] = {}
        for e in entries:
            key = normalize_key(e["key"])
            if e["family"] not in known:
                raise ValueError(f"{election_id}/{key}: famille inconnue {e['family']!r}")
            if key in out[election_id]:
                raise ValueError(f"{election_id}: clé en double {key!r}")
            out[election_id][key] = ListMapping(key, e["label"], e["family"], bool(e.get("to_validate", False)))
    return out
```

- [ ] **Step 4: Implémenter `ministry.py`**

```python
from __future__ import annotations

import re
from dataclasses import dataclass

import polars as pl

from .cog import CommuneResolver
from .families import normalize_key


@dataclass(frozen=True)
class ColumnMap:
    election_id: str
    bureau_id: str
    commune_code: pl.Expr
    inscrits: str
    votants: str
    blancs: str
    nuls: str
    exprimes: str
    cand_election_id: str
    cand_bureau_id: str
    cand_name: str
    cand_votes: str


def election_id_from_source(source_id: str) -> str | None:
    m = re.fullmatch(r"(\d{4})_pres_t1", source_id)
    return f"pres-{m.group(1)}-1" if m else None


def to_commune_tables(
    general: pl.DataFrame,
    candidates: pl.DataFrame,
    cm: ColumnMap,
    resolver: CommuneResolver,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    sources = general[cm.election_id].unique().to_list()
    id_map = {s: e for s in sources if (e := election_id_from_source(str(s)))}

    g = (
        general.filter(pl.col(cm.election_id).is_in(list(id_map)))
        .select(
            pl.col(cm.election_id).replace(id_map).alias("election_id"),
            pl.col(cm.bureau_id).alias("bureau"),
            cm.commune_code.cast(pl.String).alias("raw_code"),
            *[pl.col(getattr(cm, c)).alias(c) for c in ("inscrits", "votants", "blancs", "nuls", "exprimes")],
        )
    )
    code_map = {c: resolver.resolve(c) for c in g["raw_code"].unique().to_list()}
    g = g.with_columns(pl.col("raw_code").replace(code_map).alias("code"))

    participation = g.group_by(["election_id", "code"]).agg(
        *[pl.col(c).sum() for c in ("inscrits", "votants", "blancs", "nuls", "exprimes")]
    )

    c = candidates.filter(pl.col(cm.cand_election_id).is_in(list(id_map))).select(
        pl.col(cm.cand_election_id).replace(id_map).alias("election_id"),
        pl.col(cm.cand_bureau_id).alias("bureau"),
        pl.col(cm.cand_name).alias("name"),
        pl.col(cm.cand_votes).alias("voix"),
    )
    names = {n: normalize_key(str(n)) for n in c["name"].unique().to_list()}
    c = c.with_columns(pl.col("name").replace(names).alias("list_key"))
    joined = c.join(g.select("election_id", "bureau", "code"), on=["election_id", "bureau"], how="inner")
    votes = joined.group_by(["election_id", "code", "list_key"]).agg(pl.col("voix").sum())
    return participation, votes
```

- [ ] **Step 5: Écrire `etl/mappings/presidentielle.yaml`**

Fichier de données (classement par défaut). Les entrées `to_validate: true` sont les rattachements discutables à faire relire par l'utilisateur avant publication.

```yaml
families:
  - {id: extreme_gauche, label: "Extrême gauche", position: -2, color: "#7a1f1f"}
  - {id: gauche, label: "Gauche (dont écologistes EELV)", position: -1, color: "#d9534f"}
  - {id: centre, label: "Centre", position: 0, color: "#e0a800"}
  - {id: droite, label: "Droite", position: 1, color: "#3a78c2"}
  - {id: extreme_droite, label: "Extrême droite", position: 2, color: "#1b2a49"}
  - {id: divers, label: "Divers / hors axe", position: null, color: "#8a8a8a"}
  - {id: regionaliste, label: "Régionalistes", position: null, color: "#5b8c5a"}

elections:
  pres-2002-1:
    - {key: LAGUILLER, label: "Arlette Laguiller (LO)", family: extreme_gauche}
    - {key: BESANCENOT, label: "Olivier Besancenot (LCR)", family: extreme_gauche}
    - {key: GLUCKSTEIN, label: "Daniel Gluckstein (PT)", family: extreme_gauche}
    - {key: HUE, label: "Robert Hue (PCF)", family: gauche}
    - {key: JOSPIN, label: "Lionel Jospin (PS)", family: gauche}
    - {key: MAMERE, label: "Noël Mamère (Les Verts)", family: gauche}
    - {key: CHEVENEMENT, label: "Jean-Pierre Chevènement (MDC)", family: gauche, to_validate: true}
    - {key: TAUBIRA, label: "Christiane Taubira (PRG)", family: gauche}
    - {key: BAYROU, label: "François Bayrou (UDF)", family: centre}
    - {key: LEPAGE, label: "Corinne Lepage (Cap21)", family: centre, to_validate: true}
    - {key: CHIRAC, label: "Jacques Chirac (RPR)", family: droite}
    - {key: MADELIN, label: "Alain Madelin (DL)", family: droite}
    - {key: BOUTIN, label: "Christine Boutin (FRS)", family: droite}
    - {key: SAINT JOSSE, label: "Jean Saint-Josse (CPNT)", family: divers}
    - {key: LE PEN, label: "Jean-Marie Le Pen (FN)", family: extreme_droite}
    - {key: MEGRET, label: "Bruno Mégret (MNR)", family: extreme_droite}
  pres-2007-1:
    - {key: LAGUILLER, label: "Arlette Laguiller (LO)", family: extreme_gauche}
    - {key: BESANCENOT, label: "Olivier Besancenot (LCR)", family: extreme_gauche}
    - {key: SCHIVARDI, label: "Gérard Schivardi (PT)", family: extreme_gauche}
    - {key: BUFFET, label: "Marie-George Buffet (PCF)", family: gauche}
    - {key: BOVE, label: "José Bové (altermondialiste)", family: gauche, to_validate: true}
    - {key: ROYAL, label: "Ségolène Royal (PS)", family: gauche}
    - {key: VOYNET, label: "Dominique Voynet (Les Verts)", family: gauche}
    - {key: BAYROU, label: "François Bayrou (UDF)", family: centre}
    - {key: SARKOZY, label: "Nicolas Sarkozy (UMP)", family: droite}
    - {key: DE VILLIERS, label: "Philippe de Villiers (MPF)", family: droite}
    - {key: NIHOUS, label: "Frédéric Nihous (CPNT)", family: divers}
    - {key: LE PEN, label: "Jean-Marie Le Pen (FN)", family: extreme_droite}
  pres-2012-1:
    - {key: ARTHAUD, label: "Nathalie Arthaud (LO)", family: extreme_gauche}
    - {key: POUTOU, label: "Philippe Poutou (NPA)", family: extreme_gauche}
    - {key: MELENCHON, label: "Jean-Luc Mélenchon (FG)", family: gauche, to_validate: true}
    - {key: JOLY, label: "Eva Joly (EELV)", family: gauche}
    - {key: HOLLANDE, label: "François Hollande (PS)", family: gauche}
    - {key: BAYROU, label: "François Bayrou (MoDem)", family: centre}
    - {key: SARKOZY, label: "Nicolas Sarkozy (UMP)", family: droite}
    - {key: DUPONT AIGNAN, label: "Nicolas Dupont-Aignan (DLR)", family: droite, to_validate: true}
    - {key: CHEMINADE, label: "Jacques Cheminade (S&P)", family: divers, to_validate: true}
    - {key: LE PEN, label: "Marine Le Pen (FN)", family: extreme_droite}
  pres-2017-1:
    - {key: ARTHAUD, label: "Nathalie Arthaud (LO)", family: extreme_gauche}
    - {key: POUTOU, label: "Philippe Poutou (NPA)", family: extreme_gauche}
    - {key: MELENCHON, label: "Jean-Luc Mélenchon (FI)", family: gauche, to_validate: true}
    - {key: HAMON, label: "Benoît Hamon (PS)", family: gauche}
    - {key: MACRON, label: "Emmanuel Macron (EM)", family: centre}
    - {key: LASSALLE, label: "Jean Lassalle (Résistons !)", family: divers, to_validate: true}
    - {key: FILLON, label: "François Fillon (LR)", family: droite}
    - {key: DUPONT AIGNAN, label: "Nicolas Dupont-Aignan (DLF)", family: droite, to_validate: true}
    - {key: ASSELINEAU, label: "François Asselineau (UPR)", family: divers, to_validate: true}
    - {key: CHEMINADE, label: "Jacques Cheminade (S&P)", family: divers, to_validate: true}
    - {key: LE PEN, label: "Marine Le Pen (FN)", family: extreme_droite}
  pres-2022-1:
    - {key: ARTHAUD, label: "Nathalie Arthaud (LO)", family: extreme_gauche}
    - {key: POUTOU, label: "Philippe Poutou (NPA)", family: extreme_gauche}
    - {key: ROUSSEL, label: "Fabien Roussel (PCF)", family: gauche}
    - {key: MELENCHON, label: "Jean-Luc Mélenchon (LFI)", family: gauche, to_validate: true}
    - {key: JADOT, label: "Yannick Jadot (EELV)", family: gauche}
    - {key: HIDALGO, label: "Anne Hidalgo (PS)", family: gauche}
    - {key: MACRON, label: "Emmanuel Macron (LREM)", family: centre}
    - {key: LASSALLE, label: "Jean Lassalle (Résistons !)", family: divers, to_validate: true}
    - {key: PECRESSE, label: "Valérie Pécresse (LR)", family: droite}
    - {key: DUPONT AIGNAN, label: "Nicolas Dupont-Aignan (DLF)", family: droite, to_validate: true}
    - {key: ZEMMOUR, label: "Éric Zemmour (Reconquête)", family: extreme_droite}
    - {key: LE PEN, label: "Marine Le Pen (RN)", family: extreme_droite}
```

- [ ] **Step 6: Exécuter la suite et committer**

Run: `cd etl && uv run pytest -v`
Expected: PASS (tests des Tasks 4, 5, 7). Après cela, exécuter le Step 5 de la Task 6 (créer `config.py`) puis `uv run python scripts/check_config.py` jusqu'à `OK` partout.

```bash
git add etl && git commit -m "feat(etl): families mapping and ministry ingestion"
```

---

### Task 8: Agrégation par territoire, validations, export (TDD)

**Files:**
- Create: `etl/src/oripol_etl/aggregate.py`, `etl/src/oripol_etl/validate.py`, `etl/src/oripol_etl/export.py`, `etl/src/oripol_etl/pipeline.py`
- Test: `etl/tests/test_aggregate.py`, `etl/tests/test_validate.py`, `etl/tests/test_export.py`

**Interfaces:**
- Consumes: tables de la Task 7 (`participation`, `votes`), `geo` (`code, dep, reg`, issue du COG), `targets: list[str]`, mappings (Task 7).
- Produces :
  - `build_payload(election_id, participation, votes, geo, targets) -> dict[str, dict]` : `{territory_id: {inscrits, votants, blancs, nuls, exprimes, voix: {list_key: n}, precision: "commune"}}`
  - `validate(participation, votes, mappings) -> None` (lève `ValueError`)
  - `write_site_data(out, families, mappings, payloads, names)` : écrit `index.json`, `classification.json`, `elections/<id>.json`. Dans les fichiers exportés, `voix` est indexé par **identifiant complet** `<election_id>.<list_key>`.
  - `run()` dans `pipeline.py`.

- [ ] **Step 1: Écrire les tests qui échouent**

`etl/tests/test_aggregate.py` :
```python
import polars as pl

from oripol_etl.aggregate import build_payload

PART = pl.DataFrame(
    {
        "election_id": ["e"] * 4,
        "code": ["A1", "A2", "B1", "ZZ"],
        "inscrits": [100, 100, 100, 10],
        "votants": [80, 80, 80, 5],
        "blancs": [1, 1, 1, 0],
        "nuls": [1, 1, 1, 0],
        "exprimes": [78, 78, 78, 5],
    }
)
VOTES = pl.DataFrame(
    {
        "election_id": ["e"] * 7,
        "code": ["A1", "A1", "A2", "A2", "B1", "B1", "ZZ"],
        "list_key": ["X", "Y", "X", "Y", "X", "Y", "X"],
        "voix": [50, 28, 40, 38, 10, 68, 5],
    }
)
GEO = pl.DataFrame({"code": ["A1", "A2", "B1"], "dep": ["01", "01", "02"], "reg": ["R1", "R1", "R1"]})


def test_levels_and_targets():
    p = build_payload("e", PART, VOTES, GEO, targets=["A1"])
    assert set(p) == {"COM-A1", "DEP-01", "DEP-02", "REG-R1", "FR"}
    assert p["DEP-01"]["exprimes"] == 156
    assert p["DEP-01"]["voix"] == {"X": 90, "Y": 66}
    assert p["COM-A1"]["voix"] == {"X": 50, "Y": 28}
    assert p["FR"]["exprimes"] == 234  # ZZ (hors COG) ignoré
    assert p["FR"]["precision"] == "commune"
```
`etl/tests/test_validate.py` :
```python
import polars as pl
import pytest

from oripol_etl.families import ListMapping
from oripol_etl.validate import validate

M = {"e": {"X": ListMapping("X", "X", "gauche"), "Y": ListMapping("Y", "Y", "droite")}}


def tables(voix_y=28, key="Y"):
    part = pl.DataFrame({"election_id": ["e"], "code": ["A"], "exprimes": [78]})
    votes = pl.DataFrame({"election_id": ["e"] * 2, "code": ["A", "A"], "list_key": ["X", key], "voix": [50, voix_y]})
    return part, votes


def test_valid_tables_pass():
    validate(*tables(), M)


def test_sum_mismatch_raises():
    with pytest.raises(ValueError, match="somme des voix"):
        validate(*tables(voix_y=29), M)


def test_unmapped_list_raises():
    with pytest.raises(ValueError, match="sans famille"):
        validate(*tables(key="GHOST"), M)
```
`etl/tests/test_export.py` :
```python
import json

from oripol_etl.export import write_site_data
from oripol_etl.families import Family, ListMapping


def test_writes_prefixed_list_ids_and_index(tmp_path):
    families = [Family("gauche", "Gauche", -1, "#f00")]
    mappings = {"pres-2022-1": {"X": ListMapping("X", "Candidat X", "gauche")}}
    payloads = {
        "pres-2022-1": {
            "FR": {"inscrits": 10, "votants": 8, "blancs": 0, "nuls": 0, "exprimes": 8, "voix": {"X": 8}, "precision": "commune"}
        }
    }
    write_site_data(tmp_path, families, mappings, payloads, names={"FR": "France"})
    idx = json.loads((tmp_path / "index.json").read_text())
    assert idx["elections"] == [{"id": "pres-2022-1", "type": "pres", "year": 2022, "round": 1, "label": "Présidentielle 2022 – 1er tour"}]
    cls = json.loads((tmp_path / "classification.json").read_text())
    assert cls["lists"]["pres-2022-1.X"] == {"label": "Candidat X", "family": "gauche"}
    el = json.loads((tmp_path / "elections" / "pres-2022-1.json").read_text())
    assert el["territories"]["FR"]["voix"] == {"pres-2022-1.X": 8}
    names = json.loads((tmp_path / "names.json").read_text())
    assert names["FR"] == "France"
```

- [ ] **Step 2: Vérifier l'échec**

Run: `cd etl && uv run pytest tests/test_aggregate.py tests/test_validate.py tests/test_export.py -v`
Expected: FAIL (modules introuvables).

- [ ] **Step 3: Implémenter `aggregate.py`**

```python
from __future__ import annotations

import polars as pl

SUM_COLS = ["inscrits", "votants", "blancs", "nuls", "exprimes"]
LEVELS = [("COM", "code", True), ("DEP", "dep", False), ("REG", "reg", False), ("FR", None, False)]


def build_payload(
    election_id: str,
    participation: pl.DataFrame,
    votes: pl.DataFrame,
    geo: pl.DataFrame,
    targets: list[str],
) -> dict[str, dict]:
    part = participation.filter(pl.col("election_id") == election_id).join(geo, on="code", how="inner")
    vote = votes.filter(pl.col("election_id") == election_id).join(geo, on="code", how="inner")
    out: dict[str, dict] = {}
    for prefix, col, only_targets in LEVELS:
        p, v = part, vote
        if only_targets:
            p = p.filter(pl.col("code").is_in(targets))
            v = v.filter(pl.col("code").is_in(targets))
        key = pl.col(col) if col else pl.lit("")

        def tid(k: str) -> str:
            return f"{prefix}-{k}" if col else "FR"

        for row in p.group_by(key.alias("k")).agg([pl.col(c).sum() for c in SUM_COLS]).iter_rows(named=True):
            out[tid(row["k"])] = {**{c: row[c] for c in SUM_COLS}, "voix": {}, "precision": "commune"}
        for row in v.group_by([key.alias("k"), "list_key"]).agg(pl.col("voix").sum()).iter_rows(named=True):
            out[tid(row["k"])]["voix"][row["list_key"]] = row["voix"]
    return out
```

- [ ] **Step 4: Implémenter `validate.py`**

```python
from __future__ import annotations

import polars as pl

from .families import ListMapping


def validate(
    participation: pl.DataFrame,
    votes: pl.DataFrame,
    mappings: dict[str, dict[str, ListMapping]],
) -> None:
    sums = votes.group_by(["election_id", "code"]).agg(pl.col("voix").sum().alias("sum_voix"))
    bad = (
        participation.join(sums, on=["election_id", "code"], how="left")
        .with_columns(pl.col("sum_voix").fill_null(0))
        .filter(pl.col("sum_voix") != pl.col("exprimes"))
    )
    if bad.height:
        raise ValueError(f"somme des voix ≠ exprimés pour {bad.height} commune(s):\n{bad.head(10)}")

    missing = []
    for election_id, keys in votes.group_by("election_id").agg(pl.col("list_key").unique()).iter_rows():
        for k in keys:
            if k not in mappings.get(election_id, {}):
                missing.append(f"{election_id}.{k}")
    if missing:
        raise ValueError(f"candidats sans famille: {sorted(missing)}")
```

- [ ] **Step 5: Implémenter `export.py`**

```python
from __future__ import annotations

import json
from pathlib import Path

from .families import Family, ListMapping

LABELS = {"pres": "Présidentielle"}


def _parse(election_id: str) -> tuple[str, int, int]:
    kind, year, rnd = election_id.split("-")
    return kind, int(year), int(rnd)


def _label(election_id: str) -> str:
    kind, year, rnd = _parse(election_id)
    return f"{LABELS[kind]} {year} – {'1er' if rnd == 1 else f'{rnd}e'} tour"


def write_site_data(
    out: Path,
    families: list[Family],
    mappings: dict[str, dict[str, ListMapping]],
    payloads: dict[str, dict],
    names: dict[str, str],
) -> None:
    (out / "elections").mkdir(parents=True, exist_ok=True)
    ids = sorted(payloads, key=lambda e: _parse(e)[1:])
    index = {
        "elections": [
            {"id": e, "type": _parse(e)[0], "year": _parse(e)[1], "round": _parse(e)[2], "label": _label(e)}
            for e in ids
        ]
    }
    classification = {
        "families": [
            {"id": f.id, "label": f.label, "position": f.position, "color": f.color} for f in families
        ],
        "lists": {
            f"{e}.{k}": {"label": m.label, "family": m.family}
            for e in ids
            for k, m in mappings[e].items()
        },
    }
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    (out / "classification.json").write_text(json.dumps(classification, ensure_ascii=False), encoding="utf-8")
    (out / "names.json").write_text(json.dumps(names, ensure_ascii=False), encoding="utf-8")
    for e in ids:
        territories = {
            tid: {**r, "voix": {f"{e}.{k}": v for k, v in r["voix"].items()}}
            for tid, r in payloads[e].items()
        }
        (out / "elections" / f"{e}.json").write_text(
            json.dumps({"id": e, "territories": territories}, ensure_ascii=False), encoding="utf-8"
        )
```
Note : `names.json` est complété avec les noms de territoires par `fetch_contours.py` (Task 9) ; `write_site_data` fusionne avec un éventuel fichier existant — voir Step 6.

- [ ] **Step 6: Ajuster `export.py` pour ne pas écraser `names.json`, puis écrire `pipeline.py`**

Remplacer l'écriture de `names.json` par :
```python
    names_path = out / "names.json"
    existing = json.loads(names_path.read_text(encoding="utf-8")) if names_path.exists() else {}
    names_path.write_text(json.dumps({**existing, **names}, ensure_ascii=False), encoding="utf-8")
```
`etl/src/oripol_etl/pipeline.py` :
```python
from __future__ import annotations

import polars as pl

from . import config as c
from .aggregate import build_payload
from .cog import build_resolver
from .export import write_site_data
from .families import load_families, load_list_mappings
from .ministry import to_commune_tables
from .targets import chefs_lieux, population_max, select_targets
from .validate import validate


def _csv(path):
    df = pl.read_csv(path, infer_schema_length=5000)
    return df.rename({col: col.lower() for col in df.columns})


def _table(path):
    return pl.read_parquet(path) if str(path).endswith(".parquet") else pl.read_csv(path, infer_schema_length=5000)


def run() -> None:
    communes = _csv(c.COG_COMMUNES).filter(pl.col("typecom") == "COM")
    geo = communes.select(pl.col("com").alias("code"), "dep", "reg")
    current = set(geo["code"].to_list())
    resolver = build_resolver(_csv(c.COG_MOUVEMENTS), current)

    pop = pl.read_excel(c.POP_FILE, sheet_name=c.POP_SHEET, read_options={"header_row": c.POP_HEADER_ROW})
    lieux = chefs_lieux(_csv(c.COG_DEPARTEMENTS), _csv(c.COG_ARRONDISSEMENTS))
    targets_df = select_targets(population_max(pop, c.POP_ID_COL, c.POP_EXCLUDE), lieux, resolver)
    targets = [t for t in targets_df["code"].to_list() if resolver.is_current(t)]

    families = load_families(c.MAPPING)
    mappings = load_list_mappings(c.MAPPING)
    participation, votes = to_commune_tables(_table(c.GENERAL_FILE), _table(c.CANDIDATES_FILE), c.COLUMNS, resolver)
    participation = participation.join(geo.select("code"), on="code", how="inner")
    votes = votes.join(geo.select("code"), on="code", how="inner")

    validate(participation, votes, mappings)  # lève avant toute écriture
    payloads = {
        e: build_payload(e, participation, votes, geo, targets)
        for e in sorted(participation["election_id"].unique().to_list())
    }
    write_site_data(c.OUT, families, mappings, payloads, names={})
    (c.OUT / "targets.txt").write_text("\n".join(targets), encoding="utf-8")
    print(f"{len(payloads)} élections, {len(targets)} communes cibles → {c.OUT}")


if __name__ == "__main__":
    run()
```
Note : la jointure `inner` avec `geo` avant `validate` retire les codes hors COG (Français de l'étranger, etc.), conformément au Review Focus n°3.

- [ ] **Step 7: Vérifier les tests, lancer le pipeline réel, committer**

Run: `cd etl && uv run pytest -v`
Expected: PASS.

Run: `cd etl && uv run python -m oripol_etl.pipeline`
Expected: « 5 élections, N communes cibles → …/web/static/data » avec N de l'ordre de quelques centaines. Si `validate` échoue sur « somme des voix ≠ exprimés » : examiner les communes listées (probablement un parsing de colonne de la Task 6) avant tout contournement ; ne jamais affaiblir le contrôle. Contrôler aussi : total `FR` de 2022 (exprimés) ≈ 35,9 millions (hors établis hors de France), à comparer au résultat officiel.

```bash
git add etl && git commit -m "feat(etl): territory aggregation, blocking validation, site export"
```

---

### Task 9: Contours PMTiles et noms de territoires

**Files:**
- Create: `etl/scripts/fetch_contours.py`

**Interfaces:**
- Consumes: `web/static/data/targets.txt` (Task 8).
- Produces : `web/static/data/contours.pmtiles` (couches `regions`, `departements`, `communes`, chaque entité avec `properties.id` = `REG-…`/`DEP-…`/`COM-…` et `properties.name`), et `web/static/data/names.json` (mis à jour).

- [ ] **Step 1: Installer tippecanoe**

Run: `brew install tippecanoe && tippecanoe --version`
Expected: version ≥ 2.17 (sortie `.pmtiles` supportée).

- [ ] **Step 2: Écrire `fetch_contours.py`**

```python
"""Télécharge les contours actuels (API Découpage administratif) et construit contours.pmtiles."""
import json
import subprocess
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parents[2] / "web" / "static" / "data"
TMP = Path(__file__).resolve().parents[1] / "data" / "contours"
API = "https://geo.api.gouv.fr"
PARAMS = {"fields": "nom,code", "format": "geojson", "geometry": "contour"}


def collection(path: str, prefix: str, extra=None) -> dict:
    r = httpx.get(f"{API}/{path}", params={**PARAMS, **(extra or {})}, timeout=120)
    r.raise_for_status()
    return tag(r.json(), prefix)


def tag(fc: dict, prefix: str) -> dict:
    for f in fc["features"]:
        f["properties"] = {"id": f"{prefix}-{f['properties']['code']}", "name": f["properties"]["nom"]}
    return fc


def main() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    layers = {
        "regions": collection("regions", "REG"),
        "departements": collection("departements", "DEP"),
    }
    targets = (OUT / "targets.txt").read_text(encoding="utf-8").split()
    features = []
    for code in targets:
        r = httpx.get(f"{API}/communes/{code}", params=PARAMS, timeout=60)
        if r.status_code != 200:
            print("contour introuvable:", code)
            continue
        features.append(r.json())
    layers["communes"] = tag({"type": "FeatureCollection", "features": features}, "COM")

    names: dict[str, str] = {"FR": "France"}
    args = ["tippecanoe", "-o", str(OUT / "contours.pmtiles"), "-zg", "--drop-densest-as-needed", "--force"]
    for name, fc in layers.items():
        p = TMP / f"{name}.geojson"
        p.write_text(json.dumps(fc), encoding="utf-8")
        args += ["-L", f"{name}:{p}"]
        names.update({f["properties"]["id"]: f["properties"]["name"] for f in fc["features"]})
    subprocess.run(args, check=True)

    names_path = OUT / "names.json"
    existing = json.loads(names_path.read_text(encoding="utf-8")) if names_path.exists() else {}
    names_path.write_text(json.dumps({**existing, **names}, ensure_ascii=False), encoding="utf-8")
    print("OK", len(names), "noms")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Exécuter et vérifier**

Run: `cd etl && uv run python scripts/fetch_contours.py && ls -lh ../web/static/data/contours.pmtiles`
Expected: « OK N noms » avec N ≈ 18 + 101 + communes cibles ; fichier `.pmtiles` de quelques Mo. Les communes dont le contour est introuvable sont listées : si plus de quelques-unes, vérifier la résolution des codes (Task 8).

- [ ] **Step 4: Committer**

```bash
git add etl/scripts && git commit -m "feat(etl): contours pmtiles and territory names"
```

---

### Task 10: Chargement des données, séries temporelles et état applicatif (TDD)

**Files:**
- Create: `web/src/lib/data.ts`, `web/src/lib/series.ts`, `web/src/lib/app-state.svelte.ts`
- Test: `web/src/lib/series.test.ts`

**Interfaces:**
- Consumes: `score`, `familyShares` (Task 2), `encodeState`/`decodeState` (Task 3), types (Task 2).
- Produces (Tasks 11-12) :
  - `interface Dataset { elections: ElectionData[]; families: Family[]; names: Record<string,string> }`
  - `loadDataset(fetchFn: typeof fetch, base: string): Promise<Dataset>`
  - `interface SeriesPoint { electionId: string; label: string; year: number; score: number|null; shares: Partial<Record<FamilyId, number>>; abstention: number|null }`
  - `buildSeries(elections, type, territoryId, families, c): SeriesPoint[]` (élections du même type, triées, sans interpolation : élection absente du territoire → omise)
  - `app` : instance de `AppStore` (`election`, `territory`, `level`, `classification`, `snapshot()`, `hydrate(state)`).

- [ ] **Step 1: Écrire le test qui échoue**

```ts
import { describe, expect, it } from 'vitest';
import { buildSeries } from './series';
import { NO_OVERRIDES } from './score';
import type { ElectionData, Family } from './types';

const families: Family[] = [
	{ id: 'gauche', label: 'G', position: -1, color: '#000' },
	{ id: 'droite', label: 'D', position: 1, color: '#000' }
];
const mk = (id: string, year: number, territories: ElectionData['territories']): ElectionData => ({
	id,
	type: 'pres',
	year,
	round: 1,
	label: id,
	lists: { [`${id}.A`]: { label: 'A', family: 'gauche' }, [`${id}.B`]: { label: 'B', family: 'droite' } },
	territories
});
const res = (a: number, b: number) => ({
	inscrits: 200, votants: 100, blancs: 0, nuls: 0, exprimes: 100,
	voix: { A: a, B: b }, precision: 'commune' as const
});
const withIds = (id: string, r: ReturnType<typeof res>) => ({ ...r, voix: { [`${id}.A`]: r.voix.A, [`${id}.B`]: r.voix.B } });

describe('buildSeries', () => {
	const elections = [
		mk('pres-2012-1', 2012, { 'DEP-69': withIds('pres-2012-1', res(60, 40)) }),
		mk('pres-2002-1', 2002, { 'DEP-69': withIds('pres-2002-1', res(30, 70)) }),
		mk('pres-2007-1', 2007, {}),
		{ ...mk('leg-2012-1', 2012, { 'DEP-69': withIds('leg-2012-1', res(10, 90)) }), type: 'leg' }
	];

	it('sorts by year, keeps only the requested type, and omits elections without data', () => {
		const s = buildSeries(elections, 'pres', 'DEP-69', families, NO_OVERRIDES);
		expect(s.map((p) => p.year)).toEqual([2002, 2012]);
		expect(s[0].score).toBeCloseTo(0.4);
		expect(s[1].score).toBeCloseTo(-0.2);
	});

	it('computes abstention from inscrits and votants', () => {
		const s = buildSeries(elections, 'pres', 'DEP-69', families, NO_OVERRIDES);
		expect(s[0].abstention).toBeCloseTo(0.5);
	});
});
```

- [ ] **Step 2: Vérifier l'échec**

Run: `cd web && npx vitest run src/lib/series.test.ts`
Expected: FAIL (module introuvable).

- [ ] **Step 3: Implémenter `series.ts`**

```ts
import { familyShares, score } from './score';
import type { Classification, ElectionData, Family, FamilyId } from './types';

export interface SeriesPoint {
	electionId: string;
	label: string;
	year: number;
	score: number | null;
	shares: Partial<Record<FamilyId, number>>;
	abstention: number | null;
}

export function buildSeries(
	elections: ElectionData[],
	type: string,
	territoryId: string,
	families: Family[],
	c: Classification
): SeriesPoint[] {
	return elections
		.filter((e) => e.type === type && e.territories[territoryId])
		.sort((a, b) => a.year - b.year || a.round - b.round)
		.map((e) => {
			const r = e.territories[territoryId];
			return {
				electionId: e.id,
				label: e.label,
				year: e.year,
				score: score(r, e.lists, families, c),
				shares: familyShares(r, e.lists, c),
				abstention: r.inscrits > 0 ? 1 - r.votants / r.inscrits : null
			};
		});
}
```

- [ ] **Step 4: Implémenter `data.ts`**

```ts
import type { ElectionData, Family, ListInfo, TerritoryResult } from './types';

export interface Dataset {
	elections: ElectionData[];
	families: Family[];
	names: Record<string, string>;
}

interface IndexEntry { id: string; type: string; year: number; round: number; label: string }

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
```

- [ ] **Step 5: Implémenter `app-state.svelte.ts`**

```ts
import type { Classification, Level } from './types';
import type { AppState } from './url-state';

class AppStore {
	election = $state<string | null>(null);
	territory = $state<string | null>(null);
	level = $state<Level>('departements');
	classification = $state<Classification>({ positions: {}, listFamilies: {} });

	snapshot(): AppState {
		return {
			election: this.election,
			territory: this.territory,
			level: this.level,
			classification: $state.snapshot(this.classification) as Classification
		};
	}

	hydrate(s: AppState) {
		this.election = s.election;
		this.territory = s.territory;
		this.level = s.level;
		this.classification = s.classification;
	}

	setPosition(family: keyof Classification['positions'], value: number | null) {
		this.classification.positions = { ...this.classification.positions, [family]: value };
	}

	setListFamily(listId: string, family: string | null) {
		const next = { ...this.classification.listFamilies };
		if (family === null) delete next[listId];
		else next[listId] = family as never;
		this.classification.listFamilies = next;
	}

	resetClassification() {
		this.classification = { positions: {}, listFamilies: {} };
	}
}

export const app = new AppStore();
```

- [ ] **Step 6: Vérifier et committer**

Run: `cd web && npx vitest run && npx svelte-check`
Expected: tests PASS ; `svelte-check` sans erreur.

```bash
git add web/src/lib && git commit -m "feat(web): dataset loader, series builder, app state store"
```

---

### Task 11: Carte MapLibre et fiche territoire ECharts

**Files:**
- Create: `web/src/lib/components/Map.svelte`, `web/src/lib/components/TerritoryPanel.svelte`

**Interfaces:**
- Consumes: `scoreColor`/`NO_DATA_COLOR` (Task 3), `SeriesPoint` (Task 10), `Family` (Task 2).
- Produces (Task 12) :
  - `<Map level colors onselect />` : `level: Level`, `colors: Record<string,string>` (id de territoire → couleur CSS), `onselect(id: string)`.
  - `<TerritoryPanel name points families />` : `name: string`, `points: SeriesPoint[]`, `families: Family[]`.

- [ ] **Step 1: Écrire `Map.svelte`**

```svelte
<script lang="ts">
	import maplibregl from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';
	import { Protocol } from 'pmtiles';
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { NO_DATA_COLOR } from '$lib/color';
	import type { Level } from '$lib/types';

	let {
		level,
		colors,
		onselect
	}: { level: Level; colors: Record<string, string>; onselect: (id: string) => void } = $props();

	const LAYERS: Level[] = ['regions', 'departements', 'communes'];
	let container: HTMLDivElement;
	let map: maplibregl.Map | undefined;
	let ready = $state(false);

	onMount(() => {
		const protocol = new Protocol();
		maplibregl.addProtocol('pmtiles', protocol.tile);
		const m = new maplibregl.Map({
			container,
			style: {
				version: 8,
				sources: {},
				layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#eef1f4' } }]
			},
			center: [2.5, 46.6],
			zoom: 4.8,
			maxZoom: 11
		});
		map = m;
		m.addControl(new maplibregl.NavigationControl({ showCompass: false }));
		m.on('load', () => {
			m.addSource('contours', {
				type: 'vector',
				url: `pmtiles://${location.origin}${base}/data/contours.pmtiles`
			});
			for (const l of LAYERS) {
				m.addLayer({
					id: `${l}-fill`,
					type: 'fill',
					source: 'contours',
					'source-layer': l,
					paint: { 'fill-color': NO_DATA_COLOR, 'fill-opacity': 0.92 }
				});
				m.addLayer({
					id: `${l}-line`,
					type: 'line',
					source: 'contours',
					'source-layer': l,
					paint: { 'line-color': '#ffffff', 'line-width': 0.6 }
				});
				m.on('click', `${l}-fill`, (e) => {
					const id = e.features?.[0]?.properties?.id;
					if (typeof id === 'string') onselect(id);
				});
				m.on('mouseenter', `${l}-fill`, () => (m.getCanvas().style.cursor = 'pointer'));
				m.on('mouseleave', `${l}-fill`, () => (m.getCanvas().style.cursor = ''));
			}
			ready = true;
		});
		return () => {
			m.remove();
			maplibregl.removeProtocol('pmtiles');
		};
	});

	$effect(() => {
		if (!ready || !map) return;
		const m = map;
		const shown: Record<string, boolean> = {
			regions: level === 'regions',
			// les communes s'affichent par-dessus les départements (fond neutre)
			departements: level === 'departements' || level === 'communes',
			communes: level === 'communes'
		};
		for (const l of LAYERS) {
			const v = shown[l] ? 'visible' : 'none';
			m.setLayoutProperty(`${l}-fill`, 'visibility', v);
			m.setLayoutProperty(`${l}-line`, 'visibility', v);
		}
		const entries = Object.entries(colors);
		const paint = (l: Level) => {
			if (level === 'communes' && l === 'departements') return NO_DATA_COLOR;
			if (!entries.length) return NO_DATA_COLOR;
			return ['match', ['get', 'id'], ...entries.flat(), NO_DATA_COLOR];
		};
		for (const l of LAYERS) m.setPaintProperty(`${l}-fill`, 'fill-color', paint(l) as never);
	});
</script>

<div bind:this={container} class="map"></div>

<style>
	.map {
		width: 100%;
		height: 100%;
		min-height: 420px;
	}
</style>
```

- [ ] **Step 2: Écrire `TerritoryPanel.svelte`**

```svelte
<script lang="ts">
	import * as echarts from 'echarts/core';
	import { BarChart, LineChart } from 'echarts/charts';
	import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
	import { CanvasRenderer } from 'echarts/renderers';
	import { onMount } from 'svelte';
	import type { SeriesPoint } from '$lib/series';
	import type { Family } from '$lib/types';

	echarts.use([LineChart, BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

	let { name, points, families }: { name: string; points: SeriesPoint[]; families: Family[] } = $props();

	let scoreEl: HTMLDivElement;
	let sharesEl: HTMLDivElement;
	let scoreChart: echarts.ECharts | undefined;
	let sharesChart: echarts.ECharts | undefined;
	let mounted = $state(false);

	onMount(() => {
		scoreChart = echarts.init(scoreEl);
		sharesChart = echarts.init(sharesEl);
		mounted = true;
		const resize = () => {
			scoreChart?.resize();
			sharesChart?.resize();
		};
		window.addEventListener('resize', resize);
		return () => {
			window.removeEventListener('resize', resize);
			scoreChart?.dispose();
			sharesChart?.dispose();
		};
	});

	$effect(() => {
		if (!mounted) return;
		const years = points.map((p) => String(p.year));
		scoreChart?.setOption(
			{
				grid: { left: 40, right: 16, top: 24, bottom: 28 },
				tooltip: { trigger: 'axis' },
				xAxis: { type: 'category', data: years },
				yAxis: { type: 'value', min: -2, max: 2, name: 'gauche ← → droite', nameLocation: 'middle', nameGap: 28 },
				series: [
					{
						name: 'Score',
						type: 'line',
						data: points.map((p) => (p.score === null ? null : Number(p.score.toFixed(3)))),
						connectNulls: false,
						markLine: { silent: true, symbol: 'none', data: [{ yAxis: 0 }] }
					}
				]
			},
			true
		);
		sharesChart?.setOption(
			{
				grid: { left: 40, right: 16, top: 24, bottom: 28 },
				tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${(v * 100).toFixed(1)} %` },
				legend: { bottom: 0, type: 'scroll' },
				xAxis: { type: 'category', data: years },
				yAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => `${v * 100} %` } },
				series: [
					...families.map((f) => ({
						name: f.label,
						type: 'bar' as const,
						stack: 'parts',
						itemStyle: { color: f.color },
						data: points.map((p) => p.shares[f.id] ?? 0)
					})),
					{
						name: 'Abstention (rapportée aux inscrits)',
						type: 'line' as const,
						itemStyle: { color: '#555' },
						lineStyle: { type: 'dashed' as const },
						data: points.map((p) => (p.abstention === null ? null : p.abstention))
					}
				]
			},
			true
		);
	});
</script>

<section class="panel">
	<h2>{name}</h2>
	{#if points.length === 0}
		<p class="empty">Pas de données pour ce territoire.</p>
	{/if}
	<h3>Score gauche-droite</h3>
	<div bind:this={scoreEl} class="chart"></div>
	<h3>Parts des suffrages exprimés</h3>
	<div bind:this={sharesEl} class="chart tall"></div>
</section>

<style>
	.chart { width: 100%; height: 220px; }
	.chart.tall { height: 280px; }
	.empty { color: #666; font-style: italic; }
	h2 { margin: 0 0 0.5rem; }
	h3 { margin: 1rem 0 0.25rem; font-size: 0.9rem; color: #444; }
</style>
```

- [ ] **Step 3: Vérifier la compilation**

Run: `cd web && npx svelte-check`
Expected: 0 erreur (les avertissements d'accessibilité éventuels sont à lire, pas à ignorer systématiquement).

- [ ] **Step 4: Committer**

```bash
git add web/src/lib/components && git commit -m "feat(web): map and territory panel components"
```

---

### Task 12: Éditeur de classement, page principale et pages Sources/Méthodologie

**Files:**
- Create: `web/src/lib/components/RankingEditor.svelte`
- Modify: `web/src/routes/+page.svelte`
- Create: `web/src/routes/sources/+page.svelte`, `web/src/routes/methodologie/+page.svelte`

**Interfaces:**
- Consumes: `app`, `loadDataset`, `buildSeries`, `score`, `scoreColor`, `encodeState`/`decodeState`, `Map`, `TerritoryPanel` (Tasks 2-11).

- [ ] **Step 1: Écrire `RankingEditor.svelte`**

```svelte
<script lang="ts">
	import { app } from '$lib/app-state.svelte';
	import { positionOf } from '$lib/score';
	import type { Family, FamilyId, ListInfo } from '$lib/types';

	let { families, lists }: { families: Family[]; lists: Record<string, ListInfo> } = $props();

	const onAxis = (f: Family) => positionOf(f, app.classification) !== null;
</script>

<section class="editor">
	<h3>Classement (modifiable)</h3>
	{#each families as f (f.id)}
		{@const pos = positionOf(f, app.classification)}
		<div class="row">
			<span class="dot" style="background:{f.color}"></span>
			<label for={`pos-${f.id}`}>{f.label}</label>
			<label class="axis">
				<input
					type="checkbox"
					checked={onAxis(f)}
					onchange={(e) => app.setPosition(f.id, e.currentTarget.checked ? (f.position ?? 0) : null)}
				/>
				sur l'axe
			</label>
			<input
				id={`pos-${f.id}`}
				type="range"
				min="-2"
				max="2"
				step="0.25"
				disabled={pos === null}
				value={pos ?? 0}
				oninput={(e) => app.setPosition(f.id, Number(e.currentTarget.value))}
			/>
			<output>{pos === null ? '—' : pos.toFixed(2)}</output>
		</div>
	{/each}

	<details>
		<summary>Rattachement des candidats</summary>
		{#each Object.entries(lists) as [id, info] (id)}
			<div class="row">
				<span class="name">{info.label}</span>
				<select
					value={app.classification.listFamilies[id] ?? info.family}
					onchange={(e) => app.setListFamily(id, e.currentTarget.value === info.family ? null : e.currentTarget.value)}
				>
					{#each families as f (f.id)}
						<option value={f.id as FamilyId}>{f.label}</option>
					{/each}
				</select>
			</div>
		{/each}
	</details>

	<button type="button" onclick={() => app.resetClassification()}>Réinitialiser le classement</button>
</section>

<style>
	.row { display: grid; grid-template-columns: 12px 1fr auto 110px 36px; gap: 0.4rem; align-items: center; margin: 0.2rem 0; font-size: 0.85rem; }
	details .row { grid-template-columns: 1fr 150px; }
	.dot { width: 10px; height: 10px; border-radius: 50%; }
	.axis { font-size: 0.75rem; color: #555; }
	button { margin-top: 0.75rem; }
</style>
```

- [ ] **Step 2: Écrire `+page.svelte`**

```svelte
<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { app } from '$lib/app-state.svelte';
	import { scoreColor } from '$lib/color';
	import { loadDataset, type Dataset } from '$lib/data';
	import { score } from '$lib/score';
	import { buildSeries } from '$lib/series';
	import { decodeState, encodeState } from '$lib/url-state';
	import Map from '$lib/components/Map.svelte';
	import RankingEditor from '$lib/components/RankingEditor.svelte';
	import TerritoryPanel from '$lib/components/TerritoryPanel.svelte';
	import type { Level } from '$lib/types';

	let dataset = $state<Dataset | null>(null);
	let error = $state<string | null>(null);

	const PREFIX: Record<Level, string> = { regions: 'REG-', departements: 'DEP-', communes: 'COM-' };

	onMount(async () => {
		try {
			const d = await loadDataset(fetch, base);
			const state = decodeState(location.search.slice(1), new Set(d.families.map((f) => f.id)));
			const latest = d.elections.at(-1)?.id ?? null;
			state.election = d.elections.some((e) => e.id === state.election) ? state.election : latest;
			app.hydrate(state);
			dataset = d;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	});

	$effect(() => {
		if (!dataset) return;
		history.replaceState(null, '', `?${encodeState(app.snapshot())}`);
	});

	const election = $derived(dataset?.elections.find((e) => e.id === app.election) ?? null);

	const colors = $derived.by(() => {
		const out: Record<string, string> = {};
		if (!dataset || !election) return out;
		const prefix = PREFIX[app.level];
		for (const [id, r] of Object.entries(election.territories)) {
			if (!id.startsWith(prefix)) continue;
			out[id] = scoreColor(score(r, election.lists, dataset.families, app.classification));
		}
		return out;
	});

	const points = $derived(
		dataset && election && app.territory
			? buildSeries(dataset.elections, election.type, app.territory, dataset.families, app.classification)
			: []
	);
	const territoryName = $derived(
		app.territory ? (dataset?.names[app.territory] ?? app.territory) : null
	);
</script>

<svelte:head><title>Oripol – évolution politique des territoires</title></svelte:head>

{#if error}
	<p class="error">Impossible de charger les données : {error}</p>
{:else if !dataset}
	<p>Chargement…</p>
{:else}
	<div class="layout">
		<aside>
			<h1>Oripol</h1>
			<label>
				Élection
				<select bind:value={app.election}>
					{#each dataset.elections as e (e.id)}
						<option value={e.id}>{e.label}</option>
					{/each}
				</select>
			</label>
			<fieldset>
				<legend>Niveau</legend>
				{#each [['regions', 'Régions'], ['departements', 'Départements'], ['communes', 'Communes cibles']] as [v, label] (v)}
					<label><input type="radio" bind:group={app.level} value={v} /> {label}</label>
				{/each}
			</fieldset>
			{#if election}
				<RankingEditor families={dataset.families} lists={election.lists} />
			{/if}
			<p class="note">
				Score : −2 = extrême gauche, +2 = extrême droite. « France » = France entière hors
				Français établis hors de France. <a href="{base}/methodologie">Méthodologie</a> ·
				<a href="{base}/sources">Sources</a>
			</p>
		</aside>
		<main><Map level={app.level} {colors} onselect={(id) => (app.territory = id)} /></main>
		<section class="side">
			{#if territoryName}
				<TerritoryPanel name={territoryName} {points} families={dataset.families} />
			{:else}
				<p>Cliquez sur un territoire pour voir son évolution.</p>
				<button type="button" onclick={() => (app.territory = 'FR')}>Voir la France</button>
			{/if}
		</section>
	</div>
{/if}

<style>
	:global(body) { margin: 0; font-family: system-ui, sans-serif; color: #1c1c1c; }
	.layout { display: grid; grid-template-columns: 320px 1fr 380px; height: 100vh; }
	aside, .side { overflow-y: auto; padding: 1rem; }
	main { min-width: 0; }
	fieldset { border: 1px solid #ddd; margin: 0.75rem 0; }
	fieldset label { display: block; }
	.note { font-size: 0.75rem; color: #555; margin-top: 1rem; }
	.error { color: #b3261e; padding: 1rem; }
	@media (max-width: 1000px) {
		.layout { grid-template-columns: 1fr; height: auto; }
		main { height: 60vh; }
	}
</style>
```

- [ ] **Step 3: Pages Sources et Méthodologie**

`web/src/routes/sources/+page.svelte` :
```svelte
<script lang="ts">
	import { base } from '$app/paths';
</script>

<svelte:head><title>Sources – Oripol</title></svelte:head>
<main style="max-width: 46rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5">
	<p><a href="{base}/">← Retour à la carte</a></p>
	<h1>Sources</h1>
	<ul>
		<li><a href="https://www.data.gouv.fr/datasets/6481e741d4cf002ec0efec9d">Données des élections agrégées</a> (data.gouv.fr, d'après les fichiers du ministère de l'Intérieur) : résultats par bureau de vote, agrégés par commune.</li>
		<li><a href="https://www.data.gouv.fr/fr/datasets/contours-administratifs/">Contours administratifs</a> (IGN) via l'API Découpage administratif.</li>
		<li><a href="https://www.insee.fr/fr/statistiques/3698339">Historique des populations communales 1876-2023</a> (Insee) : sélection des communes ayant dépassé 30 000 habitants.</li>
		<li>Code officiel géographique (Insee) : fusions de communes, préfectures et sous-préfectures.</li>
	</ul>
	<h2>Limites connues</h2>
	<ul>
		<li>Les communes fusionnées sont regroupées dans la commune actuelle.</li>
		<li>« France » exclut les Français établis hors de France.</li>
		<li>Seule la présidentielle (1er tour, 2002-2022) est disponible dans cette version.</li>
	</ul>
</main>
```
`web/src/routes/methodologie/+page.svelte` :
```svelte
<script lang="ts">
	import { base } from '$app/paths';
</script>

<svelte:head><title>Méthodologie – Oripol</title></svelte:head>
<main style="max-width: 46rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5">
	<p><a href="{base}/">← Retour à la carte</a></p>
	<h1>Méthodologie</h1>
	<p>Chaque candidat est rattaché à une famille politique (extrême gauche, gauche, centre, droite, extrême droite, divers, régionalistes). Les écologistes (EELV et prédécesseurs) sont classés à gauche par défaut.</p>
	<p>Chaque famille a une position sur un axe de −2 (extrême gauche) à +2 (extrême droite). Le <strong>score</strong> d'un territoire est la somme, sur les familles placées sur l'axe, de leur part des suffrages exprimés multipliée par leur position. Les familles hors axe diluent le score mais figurent dans les parts affichées.</p>
	<p>Ce classement est discutable : vous pouvez modifier la position de chaque famille et le rattachement de chaque candidat ; le lien de la page conserve vos réglages.</p>
	<p>L'abstention est rapportée aux inscrits. Un territoire sans donnée n'est jamais affiché comme neutre : il apparaît en gris.</p>
	<p>Les comparaisons se font entre scrutins de même nature (ici : présidentielles, 1er tour).</p>
</main>
```

- [ ] **Step 4: Vérification de bout en bout dans le navigateur**

Run: `cd web && npm run dev` (via `preview_start` ou un terminal dédié), puis ouvrir l'URL locale.
Contrôles :
1. La carte affiche les départements colorés ; changer d'élection recolore la carte.
2. Passer à « Communes cibles » : les communes apparaissent ; cliquer sur Lyon ouvre une fiche à 5 points (2002-2022).
3. Déplacer le curseur « Gauche » : couleurs et courbes changent ; l'URL contient `p=`.
4. Copier l'URL, la rouvrir dans un nouvel onglet : même état.
5. Console du navigateur : aucune erreur.
6. Territoire hors données (ex. `?t=DEP-ZZ`) : message « Pas de données ».

Run: `cd web && npm run build && npx svelte-check && npm test`
Expected: build OK, 0 erreur svelte-check, tests PASS.

- [ ] **Step 5: Contrôle de cohérence final**

Comparer les totaux : pour 2022 1er tour, la part nationale de Macron/Le Pen/Mélenchon dans `FR` (exprimés hors établis hors de France) doit rester dans ±0,3 point des résultats officiels (27,85 % / 23,15 % / 21,95 % pour l'ensemble des exprimés). Un écart supérieur signale un problème d'ingestion à corriger avant de continuer.

- [ ] **Step 6: Committer**

```bash
git add -A && git commit -m "feat(web): ranking editor, main page, sources and methodology pages"
```

---

## Auto-revue du plan

- **Couverture du spec** : §2 périmètre (communes cibles Task 5 ; fusions Task 4), §4 précision (champ `precision` exporté, uniquement `commune` dans ce périmètre – affichage hachuré des autres précisions repoussé à la phase 3 avec les données CDSP), §5 modèle (matérialisé par les tables canoniques et JSON, pas de PostGIS dans ce plan : la source de vérité est le pipeline reproductible ; PostGIS sera introduit si les phases 2-3 en ont besoin), §6 classement/score (Tasks 2, 7, 12), §7 architecture (Tasks 8-12), §9 erreurs (Task 8), §10 tests (TDD Tasks 2-5, 7-8, 10 ; e2e manuel Task 12). Hors de ce plan : phases 2-4 (autres scrutins, CDSP, glissements, flux).
- **Écart assumé vs spec** : PostGIS n'est pas utilisé ici (inutile pour 1 type de scrutin, les contours viennent de l'API IGN). À réévaluer au plan de la phase 2.
- **Cohérence des types** : `Classification`, `ListInfo`, `TerritoryResult` (Task 2) réutilisés Tasks 3, 10, 11, 12 ; identifiant de liste `<election>.<clé>` produit par `export.py` (Task 8) et consommé par `data.ts` (Task 10) et `score.ts` ; `ColumnMap` (Task 7) consommé par `config.py` (Task 6 Step 5). `resolver.is_current` utilisé par `pipeline.py` (Task 8) est défini Task 4.
- **Dépendance d'ordre** : `config.py` (Task 6 Step 5) importe `ColumnMap` défini en Task 7, et les tests de la Task 7 n'importent pas `config`. Ordre d'exécution : 1, 2, 3, 4, 5, **7**, **6** (téléchargements, `config.py`, `check_config.py`), puis 8, 9, 10, 11, 12.
- **Risques résiduels** : noms de colonnes des jeux data.gouv/Insee (verrouillés par `check_config.py`) ; exactitude des candidats/familles (données à relire, `to_validate`) ; sommes exactes `voix == exprimés` possiblement en échec sur des données sales (le contrôle doit rester bloquant : investiguer, ne pas l'affaiblir).
