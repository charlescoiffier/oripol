<script lang="ts">
	let {
		open = $bindable(false),
		choices,
		busy,
		onrun
	}: {
		open: boolean;
		choices: { id: string; label: string }[];
		busy: boolean;
		onrun: (ids: string[]) => void;
	} = $props();
	let dialog: HTMLDialogElement;
	let off = $state<Record<string, boolean>>({}); // contenus décochés

	$effect(() => {
		if (!dialog) return;
		if (open && !dialog.open) dialog.showModal();
		if (!open && dialog.open) dialog.close();
	});
</script>

<dialog bind:this={dialog} onclose={() => (open = false)} onclick={(e) => e.target === dialog && (open = false)}>
	<div class="box">
		<h2>Exporter une image</h2>
		<p>La carte, cadrée sur le territoire sélectionné, et sa légende sont toujours incluses.</p>
		{#if choices.length}
			<fieldset>
				<legend>Ajouter</legend>
				{#each choices as c (c.id)}
					<label><input type="checkbox" checked={!off[c.id]} onchange={(e) => (off[c.id] = !e.currentTarget.checked)} />{c.label}</label>
				{/each}
			</fieldset>
		{:else}
			<p class="hint">Sélectionnez un territoire pour ajouter ses graphiques.</p>
		{/if}
		<div class="actions">
			<button class="btn" type="button" onclick={() => (open = false)}>Annuler</button>
			<button class="btn primary" type="button" disabled={busy} onclick={() => onrun(choices.filter((c) => !off[c.id]).map((c) => c.id))}>
				{busy ? 'Préparation…' : 'Télécharger le PNG'}
			</button>
		</div>
	</div>
</dialog>

<style>
	dialog {
		width: min(380px, calc(100vw - 32px));
		padding: 0;
		border: 0;
		border-radius: 10px;
		box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
	}
	dialog::backdrop {
		background: rgba(0, 0, 0, 0.35);
	}
	.box {
		padding: 16px 20px 18px;
	}
	h2 {
		font-size: 16px;
	}
	p {
		margin: 6px 0;
		color: var(--muted);
	}
	fieldset {
		margin: 10px 0 0;
		padding: 0;
		border: 0;
	}
	legend {
		padding: 0;
		margin-bottom: 4px;
		font-weight: 600;
	}
	label {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 3px 0;
	}
	.actions {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		margin-top: 16px;
	}
	.primary {
		background: var(--accent);
		border-color: var(--accent);
		color: #fff;
	}
	.primary:disabled {
		opacity: 0.6;
	}
</style>
