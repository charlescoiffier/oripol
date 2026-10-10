<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { BASE } from '../lib/paths';
	import { app } from '../lib/app-state.svelte';
	import { NO_DATA_COLOR, SCORE_DOMAIN, scoreColor } from '../lib/color';
	import { loadDataset, type Dataset } from '../lib/data';
	import { score } from '../lib/score';
	import { buildSeries } from '../lib/series';
	import { levelForId } from '../lib/search';
	import { decodeState, encodeState } from '../lib/url-state';
	import AboutModal from '../lib/components/AboutModal.svelte';
	import Map from '../lib/components/Map.svelte';
	import RankingEditor from '../lib/components/RankingEditor.svelte';
	import TerritoryPanel from '../lib/components/TerritoryPanel.svelte';
	import TerritorySearch from '../lib/components/TerritorySearch.svelte';
	import type { Level } from '../lib/types';
	import type { Focus } from '../lib/components/MapView.svelte';

	let dataset = $state<Dataset | null>(null);
	let error = $state<string | null>(null);
	let leftOpen = $state(true);
	let rightOpen = $state(true);
	let aboutOpen = $state(false);
	let focus = $state<Focus | undefined>(undefined);
	let boundsIndex: Record<string, [number, number, number, number]> | null = null;

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
		goto(`?${encodeState(app.snapshot())}`, { shallow: true, replace: true });
	});

	const election = $derived(dataset?.elections.find((e) => e.id === app.election) ?? null);

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
		dataset && election && app.territory
			? buildSeries(dataset.elections, election.type, app.territory, dataset.families, app.classification)
			: []
	);
	const territoryName = $derived(app.territory ? (dataset?.names[app.territory] ?? app.territory) : null);
	const territoryKind = $derived(
		app.territory ? KINDS[app.territory === 'FR' ? 'FR' : app.territory.split('-')[0]] : ''
	);

	function setLevel(l: Level) {
		app.level = l;
		if (l === 'pays') app.territory = 'FR';
	}

	function select(id: string) {
		app.territory = app.level === 'pays' ? 'FR' : id;
		rightOpen = true;
	}

	/** Territoire choisi dans la recherche : on le valide, on change de niveau et on zoome dessus. */
	async function goToTerritory(id: string) {
		app.level = levelForId(id);
		app.territory = id;
		rightOpen = true;
		try {
			boundsIndex ??= await (await fetch(`${BASE}/data/bounds.json`)).json();
		} catch {
			return; // sans emprises, on garde la vue actuelle
		}
		const bounds = boundsIndex?.[id];
		if (bounds) focus = { bounds };
	}
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
					<h1>Oripol</h1>
					<button class="icon-btn" type="button" aria-label="Replier le panneau" onclick={() => (leftOpen = false)}>‹</button>
				</header>

				<div class="field">
					<label for="election" class="section-title first">Élection</label>
					<select id="election" bind:value={app.election}>
						{#each dataset.elections as e (e.id)}
							<option value={e.id}>{e.label}</option>
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

				{#if election}
					<RankingEditor families={dataset.families} lists={election.lists} />
				{/if}

				<div class="about">
					<button class="btn" type="button" onclick={() => (aboutOpen = true)}>À propos</button>
				</div>
			</div>
		</aside>

		<main>
			<Map level={app.level} {colors} selected={app.territory} onselect={select} {focus} />
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
					<h3 class="section-title first">Choix du territoire</h3>
				</div>
				{#if territoryName}
					<header class="territory">
						<h2>{territoryName}</h2>
						<span class="kind">{territoryKind}</span>
					</header>
				{/if}
				<div class="search-row"><TerritorySearch names={dataset.names} onselect={goToTerritory} /></div>
				{#if territoryName}
					<TerritoryPanel {points} families={dataset.families} />
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
		align-items: center;
		gap: 6px;
		margin-bottom: 10px;
	}
	h1 {
		flex: 1;
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
		gap: 6px;
		align-items: center;
		margin-bottom: 8px;
	}
	.top .section-title {
		margin: 0;
	}
	.territory {
		display: flex;
		align-items: baseline;
		gap: 8px;
	}
	.kind {
		color: var(--muted);
		font-size: 12px;
	}
	.search-row {
		margin: 8px 0 4px;
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
