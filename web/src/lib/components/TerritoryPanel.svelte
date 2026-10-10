<script lang="ts">
	import * as echarts from 'echarts/core';
	import { BarChart, LineChart } from 'echarts/charts';
	import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components';
	import { CanvasRenderer } from 'echarts/renderers';
	import { onMount } from 'svelte';
	import { formatPercent, pointDetails } from '../format';
	import type { SeriesPoint } from '../series';
	import type { Family } from '../types';

	echarts.use([LineChart, BarChart, GridComponent, MarkLineComponent, TooltipComponent, CanvasRenderer]);

	let { points, families, territoryName }: { points: SeriesPoint[]; families: Family[]; territoryName: string } = $props();

	let orientationEl: HTMLDivElement;
	let sharesEl: HTMLDivElement;
	let orientationChart: echarts.ECharts | undefined;
	let sharesChart: echarts.ECharts | undefined;
	let mounted = $state(false);

	const usedFamilies = $derived(families.filter((f) => points.some((p) => (p.shares[f.id] ?? 0) > 0)));

	const TOOLTIP = {
		appendToBody: true,
		extraCssText: 'z-index: 10000; box-shadow: 0 4px 14px rgba(0,0,0,.18);',
		textStyle: { fontSize: 12 },
		borderColor: '#e5e5e5'
	};

	const esc = (t: string) => t.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

	/** En-tête des infobulles : élection et territoire, puis votants et blancs. */
	function tooltipHeader(p: SeriesPoint): string {
		const d = pointDetails(p);
		return (
			`<div style="font-weight:600">${esc(p.label)}</div>` +
			`<div>${esc(territoryName)}</div>` +
			`<div style="color:#666;margin:4px 0 6px">${esc(d.votants)}<br/>${esc(d.abstentions)}<br/>${esc(d.blancs)}</div>`
		);
	}

	const wording = (s: number) =>
		s <= -0.6 ? 'gauche marquée' : s <= -0.2 ? 'plutôt à gauche' : s < 0.2 ? 'centre' : s < 0.6 ? 'plutôt à droite' : 'droite marquée';

	onMount(() => {
		orientationChart = echarts.init(orientationEl);
		sharesChart = echarts.init(sharesEl);
		mounted = true;
		const resize = () => {
			orientationChart?.resize();
			sharesChart?.resize();
		};
		const ro = new ResizeObserver(resize);
		ro.observe(orientationEl);
		return () => {
			ro.disconnect();
			orientationChart?.dispose();
			sharesChart?.dispose();
		};
	});

	$effect(() => {
		if (!mounted) return;
		const years = points.map((p) => String(p.year));
		// axe symétrique autour de la ligne médiane : gauche à gauche, droite à droite
		const half = Math.max(0.3, ...points.map((p) => Math.abs(p.score ?? 0))) * 1.25;
		orientationChart?.setOption(
			{
				grid: { left: 40, right: 14, top: 8, bottom: 8 },
				tooltip: {
					...TOOLTIP,
					trigger: 'axis',
					formatter: (params: { dataIndex: number }[]) => {
						const p = points[params[0].dataIndex];
						return (
							tooltipHeader(p) +
							(p.score === null ? 'Orientation : pas de donnée' : `Orientation : ${wording(p.score)}`)
						);
					}
				},
				xAxis: {
					type: 'value',
					min: -half,
					max: half,
					axisLabel: { show: false },
					axisLine: { show: false },
					axisTick: { show: false },
					splitLine: { show: false }
				},
				// catégories de bas en haut : 2002 en bas, 2022 en haut
				yAxis: { type: 'category', data: years, axisTick: { show: false }, axisLine: { show: false } },
				series: [
					{
						name: 'Orientation',
						type: 'line',
						symbolSize: 8,
						itemStyle: { color: '#db4c3f' },
						lineStyle: { color: '#db4c3f', width: 2 },
						data: points.map((p) => (p.score === null ? null : Number(p.score.toFixed(3)))),
						markLine: {
							silent: true,
							symbol: 'none',
							label: { show: false },
							lineStyle: { color: '#bbb', type: 'dashed' },
							data: [{ xAxis: 0 }]
						}
					}
				]
			},
			true
		);
		sharesChart?.setOption(
			{
				grid: { left: 36, right: 8, top: 10, bottom: 22 },
				tooltip: {
					...TOOLTIP,
					trigger: 'axis',
					formatter: (params: { dataIndex: number; marker: string; seriesName: string; value: number | null }[]) => {
						const p = points[params[0].dataIndex];
						const rows = params
							.filter((r) => !r.seriesName.startsWith('Abstention') && r.value !== null && r.value !== undefined && (r.value as number) > 0)
							.map((r) => `<div>${r.marker}${esc(r.seriesName)} : <b>${formatPercent(r.value as number)}</b></div>`)
							.join('');
						return tooltipHeader(p) + rows;
					}
				},
				xAxis: { type: 'category', data: years, axisTick: { show: false } },
				yAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)} %` } },
				series: [
					...families.map((f) => ({
						name: f.label,
						type: 'bar' as const,
						stack: 'parts',
						itemStyle: { color: f.color },
						data: points.map((p) => p.shares[f.id] ?? 0)
					})),
					{
						name: 'Abstention (sur inscrits)',
						type: 'line' as const,
						itemStyle: { color: '#444' },
						lineStyle: { type: 'dashed' as const, width: 1.5 },
						symbolSize: 5,
						data: points.map((p) => p.abstention)
					}
				]
			},
			true
		);
	});
</script>

<section>
	{#if points.length === 0}
		<p class="empty">Pas de données pour ce territoire.</p>
	{/if}

	<h3 class="section-title">Évolution de l'orientation du vote</h3>
	<div bind:this={orientationEl} class="chart orientation"></div>
	<div class="sides"><span>← Gauche</span><span>Droite →</span></div>

	<h3 class="section-title">Répartition des votes</h3>
	<div bind:this={sharesEl} class="chart"></div>
	<ul class="legend">
		{#each usedFamilies as f (f.id)}
			<li><span class="dot" style="background:{f.color}"></span>{f.label}</li>
		{/each}
		<li><span class="dash"></span>Abstention (sur inscrits)</li>
	</ul>
</section>

<style>
	.chart {
		width: 100%;
		height: 230px;
	}
	.chart.orientation {
		height: 190px;
	}
	.sides {
		display: flex;
		justify-content: space-between;
		padding: 0 14px 0 40px;
		font-size: 11px;
		color: var(--muted);
	}
	.empty {
		color: var(--muted);
		font-style: italic;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 12px;
		margin: 6px 0 0;
		padding: 0;
		list-style: none;
		font-size: 11px;
	}
	.legend li {
		display: flex;
		align-items: center;
		gap: 5px;
	}
	.dot {
		width: 8px;
		height: 8px;
		border-radius: 2px;
	}
	.dash {
		width: 12px;
		border-top: 2px dashed #444;
	}
</style>
