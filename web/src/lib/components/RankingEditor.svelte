<script lang="ts">
	import { app } from '../app-state.svelte';
	import { positionOf } from '../score';
	import type { Family, ListInfo } from '../types';

	let { families, lists }: { families: Family[]; lists: Record<string, ListInfo> } = $props();
	// les voix non classées ne sont pas une position politique : pas de curseur
	const adjustable = $derived(families.filter((f) => f.inBase !== false));
</script>

<section>
	<div class="head">
		<h3 class="section-title">Classement</h3>
		<button class="link" type="button" onclick={() => app.resetClassification()}>Réinitialiser</button>
	</div>

	<div class="grid">
		{#each adjustable as f (f.id)}
			{@const pos = positionOf(f, app.classification)}
			<input
				type="checkbox"
				aria-label={`${f.label} : placer sur l'axe`}
				title="Placer sur l'axe gauche-droite"
				checked={pos !== null}
				onchange={(e) => app.setPosition(f.id, e.currentTarget.checked ? (f.position ?? 0) : null)}
			/>
			<label for={`pos-${f.id}`}><span class="dot" style="background:{f.color}"></span>{f.label}</label>
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
			<output>{pos === null ? '—' : pos.toFixed(2).replace(/\.?0+$/, '')}</output>
		{/each}
	</div>

	<details>
		<summary>Rattachement des candidats et nuances</summary>
		<div class="lists">
			{#each Object.entries(lists) as [id, info] (id)}
				<span class="name">{info.label}</span>
				<select
					aria-label={`Famille de ${info.label}`}
					value={app.classification.listFamilies[id] ?? info.family}
					onchange={(e) =>
						app.setListFamily(
							id,
							e.currentTarget.value === info.family ? null : (e.currentTarget.value as Family['id'])
						)}
				>
					{#each families as f (f.id)}
						<option value={f.id}>{f.label}</option>
					{/each}
				</select>
			{/each}
		</div>
	</details>
</section>

<style>
	.head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
	}
	.head .section-title {
		margin-bottom: 6px;
	}
	.link {
		border: 0;
		background: none;
		padding: 0;
		color: var(--accent);
		font-size: 12px;
	}
	.grid {
		display: grid;
		grid-template-columns: 14px 1fr 84px 30px;
		align-items: center;
		gap: 6px 8px;
	}
	.grid label {
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
		font-size: 12px;
	}
	.dot {
		flex: none;
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}
	input[type='checkbox'] {
		margin: 0;
		accent-color: var(--accent);
	}
	input[type='range'] {
		width: 100%;
		height: 12px;
		margin: 0;
		background: transparent;
		-webkit-appearance: none;
		appearance: none;
	}
	input[type='range']::-webkit-slider-runnable-track {
		height: 2px;
		border-radius: 1px;
		background: #d4d4d4;
	}
	input[type='range']::-moz-range-track {
		height: 2px;
		border-radius: 1px;
		background: #d4d4d4;
	}
	input[type='range']::-webkit-slider-thumb {
		-webkit-appearance: none;
		width: 10px;
		height: 10px;
		margin-top: -4px;
		border: 0;
		border-radius: 50%;
		background: var(--accent);
	}
	input[type='range']::-moz-range-thumb {
		width: 10px;
		height: 10px;
		border: 0;
		border-radius: 50%;
		background: var(--accent);
	}
	input[type='range']:disabled::-webkit-slider-thumb {
		background: #b5b5b5;
	}
	input[type='range']:disabled::-moz-range-thumb {
		background: #b5b5b5;
	}
	output {
		font-size: 11px;
		color: var(--muted);
		text-align: right;
	}
	details {
		margin-top: 10px;
		font-size: 12px;
	}
	summary {
		cursor: pointer;
		color: var(--muted);
	}
	.lists {
		display: grid;
		grid-template-columns: 1fr 120px;
		gap: 4px 8px;
		align-items: center;
		margin-top: 6px;
	}
	.lists select {
		height: 24px;
		font-size: 11px;
	}
	.name {
		font-size: 12px;
	}
</style>
