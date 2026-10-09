<script lang="ts">
	import { app } from '../app-state.svelte';
	import { positionOf } from '../score';
	import type { Family, ListInfo } from '../types';

	let { families, lists }: { families: Family[]; lists: Record<string, ListInfo> } = $props();
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
					checked={pos !== null}
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
			<div class="row list">
				<span class="name">{info.label}</span>
				<select
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
			</div>
		{/each}
	</details>

	<button type="button" onclick={() => app.resetClassification()}>Réinitialiser le classement</button>
</section>

<style>
	.row {
		display: grid;
		grid-template-columns: 12px 1fr auto 110px 36px;
		gap: 0.4rem;
		align-items: center;
		margin: 0.2rem 0;
		font-size: 0.85rem;
	}
	.row.list {
		grid-template-columns: 1fr 150px;
	}
	.dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}
	.axis {
		font-size: 0.75rem;
		color: #555;
	}
	button {
		margin-top: 0.75rem;
	}
</style>
