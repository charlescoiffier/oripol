<script lang="ts">
	import MapView, { type Bounds, type Focus } from './MapView.svelte';
	import type { Level } from '../types';

	let {
		level,
		colors,
		onselect,
		focus = undefined
	}: { level: Level; colors: Record<string, string>; onselect: (id: string) => void; focus?: Focus } = $props();

	// territoires d'outre-mer, empilés dans l'encart en bas à gauche
	const ZONES: [string, Bounds][] = [
		['Guadeloupe', [-61.9, 15.8, -60.9, 16.55]],
		['Martinique', [-61.3, 14.35, -60.75, 14.9]],
		['Guyane', [-54.7, 2.1, -51.5, 5.9]],
		['La Réunion', [55.15, -21.45, 55.9, -20.85]],
		['Mayotte', [44.95, -13.1, 45.35, -12.6]],
		['Saint-Pierre-et-Miquelon', [-56.5, 46.7, -56.1, 47.15]],
		['Saint-Martin, Saint-Barthélemy', [-63.2, 17.8, -62.75, 18.15]],
		['Polynésie française', [-154.7, -27.9, -134.4, -7.8]],
		['Nouvelle-Calédonie', [163.5, -22.4, 167.2, -19.5]],
		['Wallis-et-Futuna', [-178.3, -14.4, -176.1, -13.1]]
	];

	let overseasOpen = $state(true);

</script>

<MapView {level} {colors} {onselect} {focus} />

<aside class="overseas" aria-label="Outre-mer">
	<button type="button" class="title" aria-expanded={overseasOpen} onclick={() => (overseasOpen = !overseasOpen)}>
		Outre-mer <span>{overseasOpen ? '▾' : '▸'}</span>
	</button>
	{#if overseasOpen}
		<div class="list">
			{#each ZONES as [label, bounds] (label)}
				<figure class="box">
					<MapView {level} {colors} {onselect} {bounds} interactive={false} />
					<figcaption>{label}</figcaption>
				</figure>
			{/each}
		</div>
	{/if}
</aside>

<style>
	.overseas {
		position: absolute;
		left: 10px;
		bottom: 10px;
		z-index: 4;
		display: flex;
		flex-direction: column;
		width: 128px;
		max-height: calc(100% - 20px);
		background: rgba(255, 255, 255, 0.94);
		border: 1px solid #ddd;
		border-radius: var(--radius);
		box-shadow: 0 1px 6px rgba(0, 0, 0, 0.15);
	}
	.title {
		display: flex;
		justify-content: space-between;
		padding: 5px 8px;
		border: 0;
		border-radius: var(--radius);
		background: transparent;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--muted);
	}
	.list {
		overflow-y: auto;
		padding: 0 6px 6px;
	}
	.box {
		position: relative;
		height: 62px;
		margin: 0 0 6px;
		border: 1px solid #e1e1e1;
		border-radius: 4px;
		overflow: hidden;
		cursor: pointer;
	}
	figcaption {
		position: absolute;
		left: 4px;
		bottom: 2px;
		right: 4px;
		font-size: 10px;
		line-height: 1.15;
		color: #444;
		pointer-events: none;
		text-shadow: 0 0 3px #fff, 0 0 3px #fff, 0 0 3px #fff;
	}
</style>
