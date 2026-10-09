<script lang="ts">
	import { searchTerritories } from '../search';

	let {
		names,
		onselect
	}: { names: Record<string, string>; onselect: (id: string) => void } = $props();

	let query = $state('');
	let open = $state(false);
	let active = $state(0);

	const hits = $derived(searchTerritories(names, query, 12));

	function choose(id: string) {
		onselect(id);
		query = '';
		open = false;
	}

	function onkeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			open = true;
			active = Math.min(active + 1, hits.length - 1);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			active = Math.max(active - 1, 0);
		} else if (e.key === 'Enter' && open && hits[active]) {
			e.preventDefault();
			choose(hits[active].id);
		} else if (e.key === 'Escape') {
			open = false;
		}
	}
</script>

<div class="search">
	<input
		type="search"
		role="combobox"
		aria-expanded={open && hits.length > 0}
		aria-controls="territory-hits"
		aria-autocomplete="list"
		autocomplete="off"
		placeholder="Rechercher un territoire…"
		bind:value={query}
		oninput={() => {
			open = true;
			active = 0;
		}}
		onfocus={() => (open = true)}
		onblur={() => setTimeout(() => (open = false), 120)}
		{onkeydown}
	/>
	{#if open && hits.length}
		<ul id="territory-hits" role="listbox">
			{#each hits as h, i (h.id)}
				<li role="option" aria-selected={i === active}>
					<button
						type="button"
						class:active={i === active}
						onmousedown={(e) => e.preventDefault()}
						onclick={() => choose(h.id)}
					>
						<span class="label">{h.label}</span>
						<span class="kind">{h.kind}{h.hint ? ` · ${h.hint}` : ''}</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.search {
		position: relative;
	}
	ul {
		position: absolute;
		z-index: 20;
		left: 0;
		right: 0;
		margin: 2px 0 0;
		padding: 2px;
		list-style: none;
		max-height: 280px;
		overflow-y: auto;
		background: #fff;
		border: 1px solid #ddd;
		border-radius: var(--radius);
		box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
	}
	button {
		display: flex;
		width: 100%;
		justify-content: space-between;
		gap: 8px;
		padding: 5px 8px;
		border: 0;
		border-radius: 4px;
		background: transparent;
		text-align: left;
	}
	button:hover,
	button.active {
		background: var(--accent-soft);
	}
	.kind {
		color: var(--muted);
		font-size: 11px;
		white-space: nowrap;
	}
</style>
