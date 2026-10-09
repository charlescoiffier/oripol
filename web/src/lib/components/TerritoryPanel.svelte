<script lang="ts">
	import * as echarts from 'echarts/core';
	import { BarChart, LineChart } from 'echarts/charts';
	import { GridComponent, LegendComponent, MarkLineComponent, TooltipComponent } from 'echarts/components';
	import { CanvasRenderer } from 'echarts/renderers';
	import { onMount } from 'svelte';
	import type { SeriesPoint } from '../series';
	import type { Family } from '../types';

	echarts.use([LineChart, BarChart, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, CanvasRenderer]);

	let { name, points, families }: { name: string; points: SeriesPoint[]; families: Family[] } = $props();

	const pct = (v: number | null) => (v === null ? '—' : `${(v * 100).toFixed(1)} %`);

	let scoreEl: HTMLDivElement;
	let sharesEl: HTMLDivElement;
	let scoreChart: echarts.ECharts | undefined;
	let sharesChart: echarts.ECharts | undefined;
	let mounted = $state(false);

	onMount(() => {
		scoreChart = echarts.init(scoreEl);
		sharesChart = echarts.init(sharesEl);
		mounted = true;
		const resize = () => {
			scoreChart?.resize();
			sharesChart?.resize();
		};
		window.addEventListener('resize', resize);
		return () => {
			window.removeEventListener('resize', resize);
			scoreChart?.dispose();
			sharesChart?.dispose();
		};
	});

	$effect(() => {
		if (!mounted) return;
		const years = points.map((p) => String(p.year));
		scoreChart?.setOption(
			{
				grid: { left: 40, right: 16, top: 24, bottom: 28 },
				tooltip: { trigger: 'axis' },
				xAxis: { type: 'category', data: years },
				yAxis: { type: 'value', min: -2, max: 2, name: 'gauche ← → droite', nameLocation: 'middle', nameGap: 28 },
				series: [
					{
						name: 'Score',
						type: 'line',
						data: points.map((p) => (p.score === null ? null : Number(p.score.toFixed(3)))),
						connectNulls: false,
						markLine: { silent: true, symbol: 'none', data: [{ yAxis: 0 }] }
					}
				]
			},
			true
		);
		sharesChart?.setOption(
			{
				grid: { left: 40, right: 16, top: 24, bottom: 40 },
				tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${(v * 100).toFixed(1)} %` },
				legend: { bottom: 0, type: 'scroll' },
				xAxis: { type: 'category', data: years },
				yAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => `${v * 100} %` } },
				series: [
					...families.map((f) => ({
						name: f.label,
						type: 'bar' as const,
						stack: 'parts',
						itemStyle: { color: f.color },
						data: points.map((p) => p.shares[f.id] ?? 0)
					})),
					{
						name: 'Abstention (rapportée aux inscrits)',
						type: 'line' as const,
						itemStyle: { color: '#555' },
						lineStyle: { type: 'dashed' as const },
						data: points.map((p) => p.abstention)
					}
				]
			},
			true
		);
	});
</script>

<section class="panel">
	<h2>{name}</h2>
	{#if points.length === 0}
		<p class="empty">Pas de données pour ce territoire.</p>
	{/if}
	<h3>Score gauche-droite</h3>
	<div bind:this={scoreEl} class="chart"></div>
	<h3>Parts des suffrages exprimés</h3>
	<div bind:this={sharesEl} class="chart tall"></div>
	{#if points.length}
		<table>
			<caption>Données du territoire</caption>
			<thead>
				<tr><th>Année</th><th>Précision</th><th>Score</th><th>Abstention</th><th>Blancs + nuls</th></tr>
			</thead>
			<tbody>
				{#each points as p (p.electionId)}
					<tr>
						<td>{p.year}</td>
						<td>{p.precision}</td>
						<td>{p.score === null ? '—' : p.score.toFixed(2)}</td>
						<td>{pct(p.abstention)}</td>
						<td>{pct(p.blancsNuls)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
		<p class="foot">Abstention et blancs + nuls sont rapportés aux inscrits ; avant 2014 les blancs sont comptés avec les nuls.</p>
	{/if}
</section>

<style>
	.chart {
		width: 100%;
		height: 220px;
	}
	.chart.tall {
		height: 300px;
	}
	.empty {
		color: #666;
		font-style: italic;
	}
	table {
		width: 100%;
		margin-top: 1rem;
		border-collapse: collapse;
		font-size: 0.8rem;
	}
	caption {
		text-align: left;
		font-weight: 600;
		margin-bottom: 0.25rem;
	}
	th,
	td {
		text-align: right;
		padding: 0.15rem 0.3rem;
		border-bottom: 1px solid #eee;
	}
	th:first-child,
	td:first-child {
		text-align: left;
	}
	.foot {
		font-size: 0.7rem;
		color: #666;
	}
	h2 {
		margin: 0 0 0.5rem;
	}
	h3 {
		margin: 1rem 0 0.25rem;
		font-size: 0.9rem;
		color: #444;
	}
</style>
