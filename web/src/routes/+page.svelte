<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { BASE } from '../lib/paths';
	import { app } from '../lib/app-state.svelte';
	import { NO_DATA_COLOR, SCORE_DOMAIN, scoreColor } from '../lib/color';
	import { loadDataset, namesFor, type Dataset, type PeopleData } from '../lib/data';
	import { defaultElection, electionForType, groupByType, menuType, shortLabel, siblings } from '../lib/elections';
	import { composeA4, composePng, fileName, imageBlock, resultsBlock, savePdf, savePng, type Legend } from '../lib/export';
	import { leader, resultRows } from '../lib/leader';
	import { applyPalette, scoreEnds } from '../lib/palette';
	import { score } from '../lib/score';
	import { buildSeries } from '../lib/series';
	import { planLevelChange } from '../lib/hierarchy';
	import { levelForId } from '../lib/search';
	import { decodeState, encodeState, type Mode } from '../lib/url-state';
	import AboutModal from '../lib/components/AboutModal.svelte';
	import ExportDialog from '../lib/components/ExportDialog.svelte';
	import ResultsPanel from '../lib/components/ResultsPanel.svelte';
	import Map from '../lib/components/Map.svelte';
	import RankingEditor from '../lib/components/RankingEditor.svelte';
	import TerritoryPanel from '../lib/components/TerritoryPanel.svelte';
	import TerritorySearch from '../lib/components/TerritorySearch.svelte';
	import type { ElectionData, Level } from '../lib/types';
	import type { Focus } from '../lib/components/MapView.svelte';

	let dataset = $state<Dataset | null>(null);
	let loaded = $state<Record<string, ElectionData>>({}); // résultats chargés à la demande
	let peopleByElection = $state<Record<string, PeopleData>>({}); // listes et candidats, chargés à la demande
	let loadError = $state<string | null>(null);
	let error = $state<string | null>(null);
	let leftOpen = $state(true);
	let rightOpen = $state(true);
	let aboutOpen = $state(false);
	let exportOpen = $state(false);
	let exporting = $state(false);
	let exportNote = $state<string | null>(null);
	let mapRef = $state<{ capture: (b?: [number, number, number, number]) => Promise<HTMLCanvasElement | null> }>();
	let panelRef = $state<{ snapshot: () => { orientation: string; orientationWidth: number; shares: string; legend: { label: string; color: string; dashed?: boolean }[] } | null }>();
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
	const MODES: [Mode, string][] = [
		['classique', 'Classique'],
		['evolution', 'Évolution']
	];
	const MOBILE = 760; // largeur en dessous de laquelle la page passe sur une colonne
	const STEPS = 40; // couleurs quantifiées : la carte des 35 000 communes reste légère à recolorer

	onMount(async () => {
		if (window.innerWidth < MOBILE) {
			// une colonne : les panneaux sont affichés les uns sous les autres, sans repli
			leftOpen = true;
			rightOpen = true;
		} else if (window.innerWidth < 1000) rightOpen = false;
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
		if (!dataset || !app.election || !app.territory || app.mode !== 'evolution') return;
		for (const s of siblings(dataset.index, app.election)) ensure(s.id);
	});

	// noms des candidats : seulement utiles au mode classique, quand le scrutin en dispose
	$effect(() => {
		const id = app.election;
		// inutile tant qu'aucun territoire n'est choisi et que la carte n'est pas au niveau des communes
		if (!dataset || !id || app.mode !== 'classique' || peopleByElection[id]) return;
		if (!app.territory && app.level !== 'communes') return;
		if (!dataset.index.find((e) => e.id === id)?.people) return;
		dataset.loadPeople(id).then(
			(p) => (peopleByElection[id] = p),
			() => {} // sans les noms, la fiche garde les libellés de nuance
		);
	});

	const election = $derived(app.election ? (loaded[app.election] ?? null) : null);
	const electionGroups = $derived(dataset ? groupByType(dataset.index) : []);
	const currentType = $derived(menuType(dataset?.index.find((e) => e.id === app.election)?.type ?? '') || null);
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

	// familles recolorées selon la palette (standard ou adaptée aux daltoniens)
	const families = $derived(dataset ? applyPalette(dataset.families, app.palette) : []);

	const colors = $derived.by(() => {
		const out: Record<string, string> = {};
		if (!dataset || !election) return out;
		const ds = dataset;
		const cache = new globalThis.Map<number | null, string>();
		const colorOf = (s: number | null) => {
			const q = quantized(s);
			let c = cache.get(q);
			if (c === undefined) cache.set(q, (c = scoreColor(q, app.palette)));
			return c;
		};
		// mode classique : couleur de la famille de la liste arrivée en tête
		const detail = app.election ? peopleByElection[app.election]?.lists : undefined;
		const colorOfResult = (r: ElectionData['territories'][string], id: string) => {
			if (app.mode === 'classique') {
				// dans une commune, la liste arrivée en tête est une liste précise, pas une nuance cumulée
				const lead = leader(r, election.lists, families, app.classification, detail?.[id]);
				return families.find((f) => f.id === lead?.family)?.color ?? NO_DATA_COLOR;
			}
			return colorOf(score(r, election.lists, ds.families, app.classification));
		};
		const prefix = PREFIX[app.level];
		if (app.level === 'pays') {
			const fr = election.territories.FR;
			const c = fr ? colorOfResult(fr, 'FR') : NO_DATA_COLOR;
			// un seul territoire : tous les départements, même ceux sans résultat à ce scrutin, prennent la couleur du pays
			for (const id of [...Object.keys(election.territories), ...Object.keys(ds.names)]) {
				if (id.startsWith(prefix)) out[id] = c;
			}
			return out;
		}
		for (const [id, r] of Object.entries(election.territories)) {
			// au niveau communes, les départements colorent le fond (communes omises au zoom large)
			if (!id.startsWith(prefix) && !(app.level === 'communes' && id.startsWith('DEP-'))) continue;
			out[id] = colorOfResult(r, id);
		}
		return out;
	});

	const points = $derived(
		dataset && app.election && app.territory
			? buildSeries(siblings(dataset.index, app.election), loaded, app.territory, dataset.families, app.classification)
			: []
	);
	const peopleData = $derived(app.election ? peopleByElection[app.election] : undefined);
	const territoryPeople = $derived(peopleData && app.territory ? namesFor(peopleData, app.territory) : undefined);
	const territoryEntries = $derived(peopleData && app.territory ? peopleData.lists[app.territory] : undefined);
	const currentResult = $derived(app.territory && election ? election.territories[app.territory] : undefined);
	const electionLabel = $derived(dataset?.index.find((e) => e.id === app.election)?.label ?? '');
	const legendFamilies = $derived(families.filter((f) => f.inBase !== false));
	const ends = $derived(scoreEnds(app.palette));

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

	async function copyLink() {
		const copied = await navigator.clipboard?.writeText(location.href).then(
			() => true,
			() => false
		);
		// repli pour les contextes où l'API moderne est refusée
		const fallback = () => {
			const t = document.createElement('textarea');
			t.value = location.href;
			t.style.cssText = 'position:fixed;opacity:0';
			document.body.append(t);
			t.select();
			const ok = document.execCommand('copy');
			t.remove();
			return ok;
		};
		exportNote =
			copied || fallback()
				? 'Lien copié dans le presse-papiers.'
				: 'Copie impossible : utilisez l’adresse de la barre du navigateur.';
		setTimeout(() => (exportNote = null), 2500);
	}

	const exportChoices = $derived([
		{ id: 'map', label: 'Carte et légende' },
		...(!app.territory
			? []
			: app.mode === 'classique'
				? [{ id: 'results', label: 'Résultats du territoire' }]
				: [
						{ id: 'orientation', label: 'Évolution de l’orientation des votes' },
						{ id: 'shares', label: 'Répartition des votes' }
					])
	]);

	/** Assemble carte, légende et blocs choisis, puis les enregistre en PNG ou en page A4 (PDF). */
	async function runExport(format: 'png' | 'pdf', ids: string[]) {
		if (!dataset || exporting) return;
		exporting = true;
		try {
			await ensureGeo();
			const withMap = ids.includes('map');
			const bounds = app.territory ? boundsIndex?.[app.territory] : undefined;
			const map = withMap ? ((await mapRef?.capture(bounds)) ?? null) : null;
			const blocks: HTMLCanvasElement[] = [];
			if (app.territory && territoryName) {
				if (app.mode === 'classique' && ids.includes('results') && currentResult) {
					const rows = resultRows(currentResult, election?.lists ?? {}, app.classification, territoryPeople, territoryEntries);
					const colorOf = (f: string | undefined) => families.find((x) => x.id === f)?.color ?? '#c9c9c9';
					blocks.push(resultsBlock(electionLabel, currentResult, rows, colorOf));
				}
				if (app.mode === 'evolution') {
					const snap = panelRef?.snapshot();
					if (snap && ids.includes('orientation')) blocks.push(await imageBlock('Évolution de l’orientation des votes', snap.orientation, [], { cssWidth: snap.orientationWidth }));
					if (snap && ids.includes('shares')) blocks.push(await imageBlock('Répartition des votes', snap.shares, snap.legend));
				}
			}
			const legend: Legend = {
				noData: { label: 'Pas de donnée', color: NO_DATA_COLOR },
				...(app.mode === 'classique'
					? { swatches: legendFamilies.map((f) => ({ label: f.label, color: f.color })) }
					: { gradient: { ...ends, leftLabel: 'Gauche', rightLabel: 'Droite' } })
			};
			const input = {
				title: electionLabel,
				subtitle: `${territoryName ?? 'France'}${territoryName ? ` (${territoryKind})` : ''} · ${
					app.mode === 'classique' ? 'Famille de la liste arrivée en tête' : 'Orientation moyenne des votes'
				}`,
				map,
				showMap: withMap,
				legend,
				blocks
			};
			const name = fileName(electionLabel, territoryName ?? 'france');
			if (format === 'png') savePng(composePng(input), `${name}.png`);
			else await savePdf(composeA4(input), `${name}.pdf`);
			exportOpen = false;
		} catch (e) {
			exportNote = `Export impossible : ${e instanceof Error ? e.message : String(e)}`;
		} finally {
			exporting = false;
		}
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

				<div class="seg modes" role="radiogroup" aria-label="Mode d'affichage">
					{#each MODES as [v, label] (v)}
						<button type="button" role="radio" aria-checked={app.mode === v} class:on={app.mode === v} onclick={() => (app.mode = v)}>{label}</button>
					{/each}
				</div>
				<p class="mode-hint">
					{app.mode === 'classique'
						? 'Chaque territoire prend la couleur de la famille de la liste arrivée en tête.'
						: 'Chaque territoire est coloré selon l’orientation moyenne de ses votes, de la gauche à la droite.'}
				</p>

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
					{#if app.mode === 'classique'}
						<p class="legend-title">Famille de la liste arrivée en tête</p>
						<ul class="swatches">
							{#each legendFamilies as f (f.id)}
								<li><i style="background:{f.color}"></i>{f.label}</li>
							{/each}
						</ul>
					{:else}
						<div
							class="bar"
							style="background: linear-gradient(to right, {scoreColor(-SCORE_DOMAIN, app.palette)}, {scoreColor(0, app.palette)}, {scoreColor(SCORE_DOMAIN, app.palette)})"
						></div>
						<div class="ends"><span>Gauche</span><span>Droite</span></div>
					{/if}
					<div class="nodata"><i style="background:{NO_DATA_COLOR}"></i>Pas de donnée</div>
					<label class="palette">
						<input type="checkbox" checked={app.palette === 'daltonien'} onchange={(e) => (app.palette = e.currentTarget.checked ? 'daltonien' : 'standard')} />
						Palette adaptée aux daltoniens
					</label>
					{#if app.level === 'communes'}
						<p class="zoom-hint">Zoomez pour distinguer les communes.</p>
					{/if}
				</div>

				{#if loadError}
					<p class="loading-election error">Chargement impossible : {loadError}</p>
				{:else if !election}
					<p class="loading-election">Chargement de l'élection…</p>
				{/if}
				<RankingEditor {families} lists={electionLists} />

				<section class="share" aria-label="Partager et exporter">
					<h3 class="section-title">Partager et exporter</h3>
					<div class="seg three">
						<button type="button" onclick={copyLink}>Copier le lien</button>
						<button type="button" disabled={exporting} onclick={() => (exportOpen = true)}>Image PNG</button>
						<button type="button" disabled={exporting} onclick={() => runExport('pdf', exportChoices.map((c) => c.id))}>
							{exporting ? 'Préparation…' : 'PDF A4'}
						</button>
					</div>
					<p class="note" role="status">{exportNote ?? ''}</p>
				</section>

				<div class="about">
					<button class="help" type="button" aria-label="À propos d’Oripol" title="À propos" onclick={() => (aboutOpen = true)}>?</button>
				</div>
			</div>
		</aside>

		<main>
			<Map bind:this={mapRef} level={app.level} {colors} selected={selectedOnMap} onselect={select} onzoom={zoomTo} onclear={() => (app.territory = null)} {focus} />
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
				{#if territoryName && app.mode === 'classique'}
					<ResultsPanel {electionLabel} people={territoryPeople} entries={territoryEntries} result={currentResult} lists={election?.lists ?? {}} {families} classification={app.classification} />
				{:else if territoryName}
					<TerritoryPanel bind:this={panelRef} {points} {families} territoryName={territoryName ?? ''} />
				{:else}
					<p class="hint">Cliquez sur la carte ou recherchez un territoire pour voir {app.mode === 'classique' ? 'ses résultats' : 'son évolution'}.</p>
					<button class="btn" type="button" onclick={() => select('FR')}>Voir la France</button>
				{/if}
			</div>
		</aside>
	</div>
	<AboutModal bind:open={aboutOpen} />
	<ExportDialog bind:open={exportOpen} choices={exportChoices} busy={exporting} onrun={(ids) => runExport('png', ids)} />
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
	/* les éléments de la colonne ne rétrécissent pas : sur un écran bas, la colonne défile au lieu de les écraser */
	.inner > :global(*) {
		flex-shrink: 0;
	}
	.about {
		margin-top: auto;
		padding-top: 6px;
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
		cursor: pointer;
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
	.legend-title {
		margin: 0 0 4px;
	}
	.swatches {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 2px 8px;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.swatches li {
		display: flex;
		align-items: center;
		gap: 5px;
	}
	.swatches i {
		flex: none;
		width: 10px;
		height: 10px;
		border-radius: 2px;
	}
	.palette {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-top: 8px;
	}
	.palette input {
		margin: 0;
		accent-color: var(--accent);
	}
	.modes {
		grid-template-columns: repeat(2, 1fr);
	}
	.mode-hint {
		margin: 6px 0 18px;
		font-size: 11px;
		line-height: 1.35;
		color: var(--muted);
	}
	.seg.three {
		grid-template-columns: repeat(3, 1fr);
	}
	.seg button:disabled {
		opacity: 0.6;
	}
	/* emplacement réservé (deux lignes) : le message temporaire ne fait pas sauter la mise en page */
	.note {
		min-height: 2.7em;
		margin: 6px 0 0;
		font-size: 11px;
		line-height: 1.35;
		color: var(--muted);
	}
	/* la rangée coupe son débordement : le contour du focus doit rester à l'intérieur */
	.seg button:focus-visible {
		outline-offset: -2px;
	}
	.help {
		display: grid;
		place-items: center;
		width: 28px;
		height: 28px;
		padding: 0;
		border: 1px solid #ddd;
		border-radius: 50%;
		background: #fff;
		color: var(--muted);
		font-size: 14px;
		font-weight: 600;
		line-height: 1;
	}
	.help:hover {
		background: #f4f4f4;
		color: var(--text);
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
	@media (max-width: 760px) {
		.layout {
			display: block;
			height: auto;
		}
		aside {
			overflow: visible;
		}
		.inner,
		.right .inner {
			width: auto;
			height: auto;
			overflow: visible;
		}
		main {
			height: 70vh;
			min-height: 360px;
		}
		.handle,
		header .icon-btn,
		.top {
			display: none;
		}
		.left {
			border-right: 0;
			border-bottom: 1px solid var(--line);
		}
		.right {
			border-left: 0;
			border-top: 1px solid var(--line);
		}
	}
	@media (max-width: 1000px) {
		:global(:root) {
			--left: 250px;
			--right: 300px;
		}
	}
</style>
