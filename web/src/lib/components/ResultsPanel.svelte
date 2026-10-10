<script lang="ts">
	import { formatCount, formatPercent } from '../format';
	import { leader, resultRows } from '../leader';
	import type { Classification, Family, ListInfo, TerritoryResult } from '../types';

	let {
		electionLabel,
		result,
		lists,
		families,
		classification,
		people = {}
	}: {
		electionLabel: string;
		result: TerritoryResult | null | undefined;
		lists: Record<string, ListInfo>;
		families: Family[];
		classification: Classification;
		/** Candidats ou têtes de liste du territoire (clés `<élection>.<liste>`), quand ils sont connus. */
		people?: Record<string, string>;
	} = $props();

	const colorOf = (id: string | undefined) => families.find((f) => f.id === id)?.color ?? '#c9c9c9';
	const rows = $derived(result ? resultRows(result, lists, classification, people) : []);
	const lead = $derived(result ? leader(result, lists, families, classification) : null);
	const leadFamily = $derived(families.find((f) => f.id === lead?.family));
	const maxShare = $derived(Math.max(0.01, ...rows.map((r) => r.share)));
	const abstentions = $derived(result ? Math.max(0, result.inscrits - result.votants) : 0);
	const ofInscrits = (n: number) => (result && result.inscrits > 0 ? ` (${formatPercent(n / result.inscrits)})` : '');
	// avant 2017, le fichier source ne sépare pas les blancs des nuls
	const blancsMerged = $derived(!!result && result.blancs === 0 && result.nuls > 0);
</script>

<section>
	<h3 class="section-title">Résultats</h3>
	<p class="election">{electionLabel}</p>
	{#if !result}
		<p class="empty">Pas de résultat pour ce territoire à ce scrutin.</p>
	{:else}
		<p class="lead">
			{#if leadFamily && lead}
				<i style="background:{leadFamily.color}"></i>Couleur sur la carte : {leadFamily.label.toLowerCase()}, d'après
				« {people[lead.listId] ?? lists[lead.listId]?.label ?? lead.listId} » (les voix sans étiquette ne comptent pas).
			{:else}
				Aucune liste étiquetée : territoire en gris sur la carte.
			{/if}
		</p>
		<table>
			<thead>
				<tr><th>Liste ou candidat</th><th class="num">Voix</th><th class="num">% exprimés</th></tr>
			</thead>
			<tbody>
				{#each rows as r (r.listId)}
					<tr>
						<td>
							<span class="name">
								<i style="background:{colorOf(r.family)}"></i>
								{#if r.person}
									<span class="who">{r.person}<small>{r.label}</small></span>
								{:else}
									{r.label}
								{/if}
							</span>
							<span class="bar" style="width:{(r.share / maxShare) * 100}%; background:{colorOf(r.family)}"></span>
						</td>
						<td class="num">{formatCount(r.voix)}</td>
						<td class="num">{formatPercent(r.share)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
		<dl class="turnout">
			<div><dt>Inscrits</dt><dd>{formatCount(result.inscrits)}</dd></div>
			<div><dt>Abstentions</dt><dd>{formatCount(abstentions)}{ofInscrits(abstentions)}</dd></div>
			<div><dt>Votants</dt><dd>{formatCount(result.votants)}{ofInscrits(result.votants)}</dd></div>
			{#if blancsMerged}
				<div><dt>Blancs et nuls</dt><dd>{formatCount(result.nuls)}{ofInscrits(result.nuls)}</dd></div>
			{:else}
				<div><dt>Blancs</dt><dd>{formatCount(result.blancs)}{ofInscrits(result.blancs)}</dd></div>
				<div><dt>Nuls</dt><dd>{formatCount(result.nuls)}{ofInscrits(result.nuls)}</dd></div>
			{/if}
			<div><dt>Exprimés</dt><dd>{formatCount(result.exprimes)}</dd></div>
		</dl>
	{/if}
</section>

<style>
	.election {
		margin: 0 0 6px;
		color: var(--muted);
	}
	.lead {
		margin: 0 0 8px;
		font-size: 11.5px;
		color: var(--muted);
	}
	.lead i {
		display: inline-block;
		width: 8px;
		height: 8px;
		margin-right: 5px;
		border-radius: 2px;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 12px;
	}
	th {
		padding: 0 0 4px;
		font-size: 10.5px;
		font-weight: 600;
		text-align: left;
		color: var(--muted);
	}
	td {
		position: relative;
		padding: 4px 0 6px;
		border-top: 1px solid var(--line);
		vertical-align: top;
	}
	.num {
		padding-left: 8px;
		text-align: right;
		white-space: nowrap;
		font-variant-numeric: tabular-nums;
	}
	.name {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.who {
		display: flex;
		flex-direction: column;
		line-height: 1.25;
	}
	.who small {
		font-size: 10.5px;
		color: var(--muted);
	}
	.name i {
		flex: none;
		width: 8px;
		height: 8px;
		border-radius: 2px;
	}
	.bar {
		display: block;
		height: 3px;
		margin-top: 3px;
		border-radius: 2px;
		opacity: 0.8;
	}
	.turnout {
		margin: 12px 0 0;
		padding-top: 8px;
		border-top: 2px solid var(--line);
		font-size: 12px;
	}
	.turnout div {
		display: flex;
		justify-content: space-between;
		gap: 8px;
		padding: 1px 0;
	}
	dt {
		color: var(--muted);
	}
	dd {
		margin: 0;
		font-variant-numeric: tabular-nums;
	}
	.empty {
		color: var(--muted);
		font-style: italic;
	}
</style>
