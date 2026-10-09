<script lang="ts">
	import { onMount } from 'svelte';
	import { replaceState } from '$app/navigation';
	import { BASE } from '../lib/paths';
	import { app } from '../lib/app-state.svelte';
	import { NO_DATA_COLOR, SCORE_DOMAIN, scoreColor } from '../lib/color';
	import { loadDataset, type Dataset } from '../lib/data';
	import { score } from '../lib/score';
	import { buildSeries } from '../lib/series';
	import { decodeState, encodeState } from '../lib/url-state';
	import Map from '../lib/components/Map.svelte';
	import RankingEditor from '../lib/components/RankingEditor.svelte';
	import TerritoryPanel from '../lib/components/TerritoryPanel.svelte';
	import type { Level } from '../lib/types';

	let dataset = $state<Dataset | null>(null);
	let error = $state<string | null>(null);

	const PREFIX: Record<Level, string> = { regions: 'REG-', departements: 'DEP-', communes: 'COM-' };
	const LEVEL_CHOICES: [Level, string][] = [
		['regions', 'Régions'],
		['departements', 'Départements'],
		['communes', 'Communes cibles']
	];

	onMount(async () => {
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
		replaceState(`?${encodeState(app.snapshot())}`, {});
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

	const choices = $derived.by(() => {
		if (!dataset) return [];
		const prefix = PREFIX[app.level];
		return Object.entries(dataset.names)
			.filter(([id]) => id.startsWith(prefix))
			.sort((a, b) => a[1].localeCompare(b[1], 'fr'));
	});

	const points = $derived(
		dataset && election && app.territory
			? buildSeries(dataset.elections, election.type, app.territory, dataset.families, app.classification)
			: []
	);
	const territoryName = $derived(app.territory ? (dataset?.names[app.territory] ?? app.territory) : null);
</script>

<svelte:head><title>Oripol – évolution politique des territoires</title></svelte:head>

{#if error}
	<p class="error">Impossible de charger les données : {error}</p>
{:else if !dataset}
	<p class="loading">Chargement…</p>
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
				{#each LEVEL_CHOICES as [v, label] (v)}
					<label><input type="radio" bind:group={app.level} value={v} /> {label}</label>
				{/each}
			</fieldset>
			<label>
				Territoire
				<select bind:value={app.territory}>
					<option value={null}>— choisir —</option>
					<option value="FR">France</option>
					{#each choices as [id, name] (id)}
						<option value={id}>{name}</option>
					{/each}
				</select>
			</label>
			<div class="legend" aria-label="Légende du score">
				<div class="bar" style="background: linear-gradient(to right, {scoreColor(-SCORE_DOMAIN)}, {scoreColor(0)}, {scoreColor(SCORE_DOMAIN)})"></div>
				<div class="ticks"><span>−{SCORE_DOMAIN} gauche</span><span>0</span><span>+{SCORE_DOMAIN} droite</span></div>
				<div class="nodata"><span class="swatch" style="background:{NO_DATA_COLOR}"></span> Pas de donnée / hors périmètre</div>
			</div>
			{#if election}
				<RankingEditor families={dataset.families} lists={election.lists} />
			{/if}
			<p class="note">
				Score sur l'axe −2 (extrême gauche) à +2 (extrême droite) ; la couleur sature à ±1. « France » = France métropolitaine et DOM
				(hors Français établis hors de France et collectivités d'outre-mer).
				<a href="{BASE}/methodologie">Méthodologie</a> · <a href="{BASE}/sources">Sources</a>
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
	:global(body) {
		margin: 0;
		font-family: system-ui, sans-serif;
		color: #1c1c1c;
	}
	.layout {
		display: grid;
		grid-template-columns: 320px 1fr 380px;
		height: 100vh;
	}
	aside,
	.side {
		overflow-y: auto;
		padding: 1rem;
	}
	main {
		min-width: 0;
	}
	fieldset {
		border: 1px solid #ddd;
		margin: 0.75rem 0;
	}
	fieldset label {
		display: block;
	}
	.legend {
		margin: 0.75rem 0;
		font-size: 0.75rem;
	}
	.legend .bar {
		height: 10px;
		border: 1px solid #ccc;
	}
	.legend .ticks {
		display: flex;
		justify-content: space-between;
	}
	.legend .swatch {
		display: inline-block;
		width: 10px;
		height: 10px;
		border: 1px solid #aaa;
		vertical-align: middle;
	}
	.note {
		font-size: 0.75rem;
		color: #555;
		margin-top: 1rem;
	}
	.error {
		color: #b3261e;
		padding: 1rem;
	}
	.loading {
		padding: 1rem;
	}
	@media (max-width: 1000px) {
		.layout {
			grid-template-columns: 1fr;
			height: auto;
		}
		main {
			height: 60vh;
		}
	}
</style>
