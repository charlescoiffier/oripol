<script lang="ts">
	import * as echarts from 'echarts/core';
	import { BarChart, LineChart } from 'echarts/charts';
	import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components';
	import { CanvasRenderer } from 'echarts/renderers';
	import { onMount } from 'svelte';
	import type { SeriesPoint } from '../series';
	import type { Family } from '../types';

	echarts.use([LineChart, BarChart, GridComponent, MarkLineComponent, TooltipComponent, CanvasRenderer]);

	let {
		name,
		kind,
		points,
		families
	}: { name: string; kind: string; points: SeriesPoint[]; families: Family[] } = $props();

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
		const scores = points.flatMap((p) => (p.score === null ? [] : [p.score]));
		const lo = Math.min(0, ...scores);
		const hi = Math.max(0, ...scores);
		const pad = Math.max(0.25, (hi - lo) * 0.2);
		orientationChart?.setOption(
			{
				grid: { left: 8, right: 8, top: 10, bottom: 22 },
				tooltip: {
					...TOOLTIP,
					trigger: 'axis',
					formatter: (params: { dataIndex: number }[]) => {
						const p = points[params[0].dataIndex];
						return p.score === null
							? `${p.year} : pas de donnée`
							: `<b>${p.year}</b><br/>${wording(p.score)}`;
					}
				},
				xAxis: { type: 'category', data: years, axisTick: { show: false } },
				yAxis: {
					type: 'value',
					min: lo - pad,
					max: hi + pad,
					axisLabel: { show: false },
					axisLine: { show: false },
					axisTick: { show: false },
					splitLine: { show: false }
				},
				series: [
					{
						name: 'Orientation',
						type: 'line',
						symbolSize: 7,
						itemStyle: { color: '#db4c3f' },
						lineStyle: { color: '#db4c3f', width: 2 },
						data: points.map((p) => (p.score === null ? null : Number(p.score.toFixed(3)))),
						markLine: {
							silent: true,
							symbol: 'none',
							label: { show: false },
							lineStyle: { color: '#ddd', type: 'dashed' },
							data: [{ yAxis: 0 }]
						}
					}
				]
			},
			true
		);
		sharesChart?.setOption(
			{
				grid: { left: 36, right: 8, top: 10, bottom: 22 },
				tooltip: { ...TOOLTIP, trigger: 'axis', valueFormatter: (v: number) => `${(v * 100).toFixed(1)} %` },
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
	<header>
		<h2>{name}</h2>
		<span class="kind">{kind}</span>
	</header>
	{#if points.length === 0}
		<p class="empty">Pas de données pour ce territoire.</p>
	{/if}

	<h3>Évolution de l'orientation du vote</h3>
	<p class="axis-hint">Plus haut : plus à droite · plus bas : plus à gauche</p>
	<div bind:this={orientationEl} class="chart short"></div>

	<h3>Répartition des votes</h3>
	<div bind:this={sharesEl} class="chart"></div>
	<ul class="legend">
		{#each usedFamilies as f (f.id)}
			<li><span class="dot" style="background:{f.color}"></span>{f.label}</li>
		{/each}
		<li><span class="dash"></span>Abstention (sur inscrits)</li>
	</ul>
</section>

<style>
	header {
		display: flex;
		align-items: baseline;
		gap: 8px;
	}
	h2 {
		font-size: 17px;
	}
	.kind {
		color: var(--muted);
		font-size: 12px;
	}
	h3 {
		margin: 16px 0 4px;
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--muted);
	}
	.axis-hint {
		margin: 0;
		font-size: 11px;
		color: var(--muted);
	}
	.chart {
		width: 100%;
		height: 230px;
	}
	.chart.short {
		height: 150px;
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
