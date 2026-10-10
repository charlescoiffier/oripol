<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { BASE } from '../lib/paths';
	import { app } from '../lib/app-state.svelte';
	import { NO_DATA_COLOR, SCORE_DOMAIN, scoreColor } from '../lib/color';
	import { loadDataset, type Dataset } from '../lib/data';
	import { defaultElection, electionForType, groupByType, shortLabel, siblings } from '../lib/elections';
	import { score } from '../lib/score';
	import { buildSeries } from '../lib/series';
	import { planLevelChange } from '../lib/hierarchy';
	import { levelForId } from '../lib/search';
	import { decodeState, encodeState } from '../lib/url-state';
	import AboutModal from '../lib/components/AboutModal.svelte';
	import Map from '../lib/components/Map.svelte';
	import RankingEditor from '../lib/components/RankingEditor.svelte';
	import TerritoryPanel from '../lib/components/TerritoryPanel.svelte';
	import TerritorySearch from '../lib/components/TerritorySearch.svelte';
	import type { ElectionData, Level } from '../lib/types';
	import type { Focus } from '../lib/components/MapView.svelte';

	let dataset = $state<Dataset | null>(null);
	let loaded = $state<Record<string, ElectionData>>({}); // résultats chargés à la demande
	let loadError = $state<string | null>(null);
	let error = $state<string | null>(null);
	let leftOpen = $state(true);
	let rightOpen = $state(true);
	let aboutOpen = $state(false);
	let focus = $state<Focus | undefined>(undefined);
	let boundsIndex: Record<string, [number, number, number, number]> | null = null;
	let parents: Record<string, string> = {};

	const PREFIX: Record<Level, string> = { pays: 'DEP-', regions: 'REG-', departements: 'DEP-', communes: 'COM-' };
	const LEVELS: [Level, string][] = [
		['pays', 'Pays'],
		['regions', 'Régions'],
		['departements', 'Départements'],
		['communes', 'Communes']
	];
	const KINDS: Record<string, string> = { FR: 'Pays', REG: 'Région', DEP: 'Département', COM: 'Commune' };
	const STEPS = 40; // couleurs quantifiées : la carte des 35 000 communes reste légère à recolorer

	onMount(async () => {
		if (window.innerWidth < 1000) rightOpen = false;
		try {
			const d = await loadDataset(fetch, BASE);
			const state = decodeState(location.search.slice(1), new Set(d.families.map((f) => f.id)));
			state.election = d.index.some((e) => e.id === state.election) ? state.election : defaultElection(d.index);
			app.hydrate(state);
			dataset = d;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	});

	$effect(() => {
		if (!dataset) return;
		goto(`?${encodeState(app.snapshot())}`, { shallow: true, replace: true });
	});

	const pending = new Set<string>();
	function ensure(id: string) {
		if (!dataset || loaded[id] || pending.has(id)) return;
		pending.add(id);
		dataset
			.loadElection(id)
			.then((e) => (loaded[id] = e))
			.catch((e) => (loadError = e instanceof Error ? e.message : String(e)))
			.finally(() => pending.delete(id));
	}

	// l'élection affichée, puis (une fois un territoire choisi) les élections comparables pour sa courbe
	$effect(() => {
		if (app.election) ensure(app.election);
	});
	$effect(() => {
		if (!dataset || !app.election || !app.territory) return;
		for (const s of siblings(dataset.index, app.election)) ensure(s.id);
	});

	const election = $derived(app.election ? (loaded[app.election] ?? null) : null);
	const electionGroups = $derived(dataset ? groupByType(dataset.index) : []);
	const currentType = $derived(dataset?.index.find((e) => e.id === app.election)?.type ?? null);
	const currentEntries = $derived(electionGroups.find((g) => g.type === currentType)?.entries ?? []);

	function changeType(type: string) {
		if (dataset) app.election = electionForType(dataset.index, type, app.election);
	}
	const electionLists = $derived(
		app.election && dataset
			? Object.fromEntries(Object.entries(dataset.lists).filter(([id]) => id.startsWith(`${app.election}.`)))
			: {}
	);

	const quantized = (s: number | null) => {
		if (s === null) return null;
		const c = Math.max(-SCORE_DOMAIN, Math.min(SCORE_DOMAIN, s));
		return Math.round((c / SCORE_DOMAIN) * STEPS) / STEPS * SCORE_DOMAIN;
	};

	const colors = $derived.by(() => {
		const out: Record<string, string> = {};
		if (!dataset || !election) return out;
		const cache = new globalThis.Map<number | null, string>();
		const colorOf = (s: number | null) => {
			const q = quantized(s);
			let c = cache.get(q);
			if (c === undefined) cache.set(q, (c = scoreColor(q)));
			return c;
		};
		const prefix = PREFIX[app.level];
		if (app.level === 'pays') {
			const fr = election.territories.FR;
			const c = fr ? colorOf(score(fr, election.lists, dataset.families, app.classification)) : NO_DATA_COLOR;
			for (const id of Object.keys(election.territories)) if (id.startsWith(prefix)) out[id] = c;
			return out;
		}
		for (const [id, r] of Object.entries(election.territories)) {
			// au niveau communes, les départements colorent le fond (communes omises au zoom large)
			if (!id.startsWith(prefix) && !(app.level === 'communes' && id.startsWith('DEP-'))) continue;
			out[id] = colorOf(score(r, election.lists, dataset.families, app.classification));
		}
		return out;
	});

	const points = $derived(
		dataset && app.election && app.territory
			? buildSeries(siblings(dataset.index, app.election), loaded, app.territory, dataset.families, app.classification)
			: []
	);
	const territoryName = $derived(app.territory ? (dataset?.names[app.territory] ?? app.territory) : null);
	const territoryKind = $derived(
		app.territory ? KINDS[app.territory === 'FR' ? 'FR' : app.territory.split('-')[0]] : ''
	);

	/** Emprises et hiérarchie des territoires, chargées à la première utilisation. */
	async function ensureGeo(): Promise<boolean> {
		if (boundsIndex) return true;
		try {
			const [b, p] = await Promise.all([
				fetch(`${BASE}/data/bounds.json`).then((r) => r.json()),
				fetch(`${BASE}/data/parents.json`).then((r) => r.json())
			]);
			boundsIndex = b;
			parents = p;
			return true;
		} catch {
			return false; // sans emprises, on garde la vue actuelle
		}
	}

	async function focusOn(id: string) {
		if (!(await ensureGeo())) return;
		const bounds = boundsIndex?.[id];
		if (bounds) focus = { bounds }; // nouvel objet à chaque fois : le zoom se refait même sur le même territoire
	}

	/** Changement de niveau : sélection du parent / conservation du territoire, et zoom adapté. */
	async function setLevel(l: Level) {
		await ensureGeo();
		const plan = planLevelChange(app.territory, l, parents);
		app.level = l;
		app.territory = plan.territory;
		if (plan.focusId) await focusOn(plan.focusId);
	}

	function select(id: string) {
		app.territory = app.level === 'pays' ? 'FR' : id;
		rightOpen = true;
	}

	/** Double clic : sélection et zoom sur l'emprise du territoire. */
	async function zoomTo(id: string) {
		select(id);
		await focusOn(app.level === 'pays' ? 'FR' : id);
	}

	/** Territoire choisi dans la recherche : on le valide, on change de niveau et on zoome dessus. */
	async function goToTerritory(id: string) {
		app.level = levelForId(id);
		app.territory = id;
		rightOpen = true;
		await focusOn(id);
	}

	// contour de sélection : seulement si le territoire est du niveau affiché
	const selectedOnMap = $derived(app.territory && levelForId(app.territory) === app.level ? app.territory : null);
</script>

<svelte:head><title>Oripol – évolution politique des territoires</title></svelte:head>

{#if error}
	<p class="status error">Impossible de charger les données : {error}</p>
{:else if !dataset}
	<p class="status">Chargement…</p>
{:else}
	<div class="layout" style="--lw: {leftOpen ? 'var(--left)' : '0px'}; --rw: {rightOpen ? 'var(--right)' : '0px'}">
		<aside class="left" aria-label="Réglages" inert={!leftOpen}>
			<div class="inner">
				<header>
					<div class="brand">
						<h1>Oripol</h1>
						<p class="tagline">Représentation des dynamiques de vote des élections françaises</p>
					</div>
					<button class="icon-btn" type="button" aria-label="Replier le panneau" onclick={() => (leftOpen = false)}>‹</button>
				</header>

				<div class="field">
					<label for="election-type" class="section-title first">Type d'élection</label>
					<select id="election-type" value={currentType} onchange={(e) => changeType(e.currentTarget.value)}>
						{#each electionGroups as g (g.type)}
							<option value={g.type}>{g.label}</option>
						{/each}
					</select>
				</div>

				<div class="field">
					<label for="election" class="section-title">Élection</label>
					<select id="election" bind:value={app.election}>
						{#each currentEntries as e (e.id)}
							<option value={e.id}>{shortLabel(e)}</option>
						{/each}
					</select>
				</div>

				<div class="field">
					<span class="section-title" id="level-label">Niveau</span>
					<div class="seg" role="radiogroup" aria-labelledby="level-label">
						{#each LEVELS as [v, label] (v)}
							<button
								type="button"
								role="radio"
								aria-checked={app.level === v}
								class:on={app.level === v}
								onclick={() => setLevel(v)}>{label}</button
							>
						{/each}
					</div>
				</div>

				<div class="legend" aria-label="Légende de la carte">
					<div
						class="bar"
						style="background: linear-gradient(to right, {scoreColor(-SCORE_DOMAIN)}, {scoreColor(0)}, {scoreColor(SCORE_DOMAIN)})"
					></div>
					<div class="ends"><span>Gauche</span><span>Droite</span></div>
					<div class="nodata"><i style="background:{NO_DATA_COLOR}"></i>Pas de donnée</div>
					{#if app.level === 'communes'}
						<p class="zoom-hint">Zoomez pour distinguer les communes.</p>
					{/if}
				</div>

				{#if loadError}
					<p class="loading-election error">Chargement impossible : {loadError}</p>
				{:else if !election}
					<p class="loading-election">Chargement de l'élection…</p>
				{/if}
				<RankingEditor families={dataset.families} lists={electionLists} />

				<div class="about">
					<button class="btn" type="button" onclick={() => (aboutOpen = true)}>À propos</button>
				</div>
			</div>
		</aside>

		<main>
			<Map level={app.level} {colors} selected={selectedOnMap} onselect={select} onzoom={zoomTo} onclear={() => (app.territory = null)} {focus} />
			{#if !leftOpen}
				<button class="handle left-handle" type="button" aria-label="Déplier le panneau de gauche" onclick={() => (leftOpen = true)}>›</button>
			{/if}
			{#if !rightOpen}
				<button class="handle right-handle" type="button" aria-label="Déplier le panneau de droite" onclick={() => (rightOpen = true)}>‹</button>
			{/if}
		</main>

		<aside class="right" aria-label="Territoire" inert={!rightOpen}>
			<div class="inner">
				<div class="top">
					<button class="icon-btn" type="button" aria-label="Replier le panneau" onclick={() => (rightOpen = false)}>›</button>
				</div>
				<h3 class="section-title">Choix du territoire</h3>
				<div class="search-row"><TerritorySearch names={dataset.names} onselect={goToTerritory} /></div>
				{#if territoryName}
					<header class="territory">
						<h2>{territoryName}</h2>
						<span class="kind">{territoryKind}</span>
					</header>
				{/if}
				{#if territoryName}
					<TerritoryPanel {points} families={dataset.families} territoryName={territoryName ?? ''} />
				{:else}
					<p class="hint">Cliquez sur la carte ou recherchez un territoire pour voir son évolution.</p>
					<button class="btn" type="button" onclick={() => select('FR')}>Voir la France</button>
				{/if}
			</div>
		</aside>
	</div>
	<AboutModal bind:open={aboutOpen} />
{/if}

<style>
	.status {
		padding: 1rem;
	}
	.error {
		color: #b3261e;
	}
	.layout {
		display: grid;
		grid-template-columns: var(--lw) 1fr var(--rw);
		height: 100vh;
		transition: grid-template-columns 0.18s ease;
	}
	aside {
		overflow: hidden;
		background: var(--panel);
		min-width: 0;
	}
	.left {
		border-right: 1px solid var(--line);
	}
	.right {
		border-left: 1px solid var(--line);
		background: #fff;
	}
	.inner {
		display: flex;
		flex-direction: column;
		width: var(--left);
		height: 100%;
		overflow-y: auto;
		padding: 10px 14px 16px;
	}
	.about {
		margin-top: auto;
		padding-top: 18px;
	}
	.right .inner {
		width: var(--right);
	}
	header {
		display: flex;
		align-items: flex-start;
		gap: 6px;
		margin-bottom: 10px;
	}
	.brand {
		flex: 1;
		min-width: 0;
	}
	.tagline {
		margin: 1px 0 0;
		font-size: 11px;
		line-height: 1.3;
		color: var(--muted);
	}
	h1 {
		color: var(--accent);
		letter-spacing: -0.01em;
	}
	.field {
		margin-bottom: 0;
	}
	.seg {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		border: 1px solid #ddd;
		border-radius: var(--radius);
		overflow: hidden;
		background: #fff;
	}
	.seg button {
		height: 26px;
		padding: 0 2px;
		border: 0;
		border-right: 1px solid #ddd;
		background: transparent;
		font-size: 11.5px;
	}
	.seg button:last-child {
		border-right: 0;
	}
	.seg button.on {
		background: var(--accent);
		color: #fff;
	}
	.legend {
		margin: 12px 0 0;
		font-size: 11px;
		color: var(--muted);
	}
	.bar {
		height: 8px;
		border-radius: 4px;
		border: 1px solid #e2e2e2;
	}
	.ends {
		display: flex;
		justify-content: space-between;
		margin-top: 2px;
	}
	.loading-election {
		margin: 8px 0 0;
		font-size: 11px;
		font-style: italic;
		color: var(--muted);
	}
	.zoom-hint {
		margin: 6px 0 0;
		font-style: italic;
	}
	.nodata {
		display: flex;
		align-items: center;
		gap: 5px;
		margin-top: 4px;
	}
	.nodata i {
		width: 10px;
		height: 10px;
		border-radius: 2px;
	}
	main {
		position: relative;
		min-width: 0;
	}
	.handle {
		position: absolute;
		top: 10px;
		z-index: 5;
		width: 24px;
		height: 32px;
		border: 1px solid #ddd;
		background: #fff;
		color: var(--muted);
		font-size: 16px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
	}
	.left-handle {
		left: 0;
		border-radius: 0 var(--radius) var(--radius) 0;
	}
	.right-handle {
		right: 0;
		border-radius: var(--radius) 0 0 var(--radius);
	}
	.top {
		display: flex;
		margin: -4px 0 0 -6px;
	}
	.territory {
		display: flex;
		align-items: baseline;
		gap: 8px;
		margin-bottom: 2px;
	}
	.kind {
		color: var(--muted);
		font-size: 12px;
	}
	.search-row {
		margin: 0 0 14px;
	}
	.hint {
		color: var(--muted);
	}
	@media (max-width: 1000px) {
		:global(:root) {
			--left: 250px;
			--right: 300px;
		}
	}
</style>
