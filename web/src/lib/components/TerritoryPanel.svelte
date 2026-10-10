<script lang="ts">
	import * as echarts from 'echarts/core';
	import { BarChart, LineChart, ScatterChart } from 'echarts/charts';
	import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components';
	import { CanvasRenderer } from 'echarts/renderers';
	import { onMount } from 'svelte';
	import { classifiedLine, formatPercent, orientationLabel, pointDetails, statusLine } from '../format';
	import type { SeriesPoint } from '../series';
	import type { Family } from '../types';

	echarts.use([LineChart, BarChart, ScatterChart, GridComponent, MarkLineComponent, TooltipComponent, CanvasRenderer]);

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

	/** En-tête des infobulles : élection et territoire, puis votants, abstentions et blancs. */
	function tooltipHeader(p: SeriesPoint): string {
		const title = `<div style="font-weight:600">${esc(p.label)}</div><div>${esc(territoryName)}</div>`;
		if (p.status === 'absent' || p.status === 'loading') return title;
		const d = pointDetails(p);
		return (
			title +
			`<div style="color:#666;margin:4px 0 6px">${esc(d.votants)}<br/>${esc(d.abstentions)}<br/>${esc(d.blancs)}` +
			(classifiedLine(p) ? `<br/>${esc(classifiedLine(p) as string)}` : '') +
			`</div>`
		);
	}

	const note = (p: SeriesPoint): string =>
		p.status === 'loading' ? '<div>Chargement…</div>' : statusLine(p) ? `<div style="color:#666">${esc(statusLine(p) as string)}</div>` : '';

	// l'animation (points qui apparaissent en 1 s) ne se joue que lorsque le territoire ou la série change,
	// pas quand on déplace un curseur du classement
	let lastAnimated = '';
	let revealTimer: ReturnType<typeof setInterval> | undefined;
	const hasAbsent = $derived(points.some((p) => p.status === 'absent'));
	const hasUnscored = $derived(points.some((p) => p.status === 'unscored'));

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
			clearInterval(revealTimer);
			ro.disconnect();
			orientationChart?.dispose();
			sharesChart?.dispose();
		};
	});

	$effect(() => {
		if (!mounted) return;
		const years = points.map((p) => String(p.year));
		const key = `${territoryName}|${points.map((p) => p.electionId).join(',')}`;
		const complete = points.every((p) => p.status !== 'loading');
		const animate = complete && key !== lastAnimated;
		if (animate) lastAnimated = key;
		// axe symétrique autour de la ligne médiane : gauche à gauche, droite à droite
		const scores = points.flatMap((p) => (p.status === 'ok' && p.score !== null ? [Math.abs(p.score)] : []));
		const half = Math.max(0.3, ...scores) * 1.25;
		const marks = (status: 'absent' | 'unscored', visible: number) =>
			points.flatMap((p, i) => (i < visible && p.status === status ? [[0, i]] : []));
		// option du graphique avec seulement les `visible` premiers points (apparition progressive)
		const orientationOption = (visible: number) => (
			{
				animation: false, // l'apparition progressive est pilotée à la main (voir plus bas)
				grid: { left: 40, right: 14, top: 8, bottom: 8 },
				tooltip: {
					...TOOLTIP,
					trigger: 'axis',
					formatter: (params: { dataIndex: number }[]) => {
						const p = points[params[0].dataIndex];
						const line =
							p.status === 'ok' && p.score !== null ? `Orientation moyenne : ${orientationLabel(p.score)}` : '';
						return tooltipHeader(p) + (line ? `<div>${line}</div>` : '') + note(p);
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
				// années du haut vers le bas : la plus ancienne en haut
				yAxis: { type: 'category', data: years, inverse: true, axisTick: { show: false }, axisLine: { show: false } },
				series: [
					{
						name: 'Orientation moyenne',
						type: 'line',
						symbolSize: 8,
						itemStyle: { color: '#db4c3f' },
						lineStyle: { color: '#db4c3f', width: 2 },
						data: points.map((p, i) => (i < visible && p.status === 'ok' && p.score !== null ? Number(p.score.toFixed(3)) : null)),
						markLine: {
							silent: true,
							symbol: 'none',
							label: { show: false },
							lineStyle: { color: '#bbb', type: 'dashed' },
							data: [{ xAxis: 0 }]
						}
					},
					{
						// scrutin sans résultat pour ce territoire : croix grise sur la ligne médiane
						name: 'Pas de résultat',
						type: 'scatter',
						symbol: 'path://M-4,-4L4,4M4,-4L-4,4',
						symbolSize: 9,
						itemStyle: { color: '#999', borderColor: '#999', borderWidth: 1.5 },
						z: 5,
						data: marks('absent', visible)
					},
					{
						// résultat sans orientation calculable (peu de voix étiquetées) : cercle gris creux
						name: 'Orientation moyenne non calculée',
						type: 'scatter',
						symbol: 'circle',
						symbolSize: 8,
						itemStyle: { color: '#fff', borderColor: '#999', borderWidth: 1.5 },
						z: 5,
						data: marks('unscored', visible)
					}
				]
			}
		);

		// ECharts ne rejoue pas son animation d'entrée quand on remplace les données d'un graphique déjà affiché :
		// on révèle donc les points un à un, en environ 1 seconde
		clearInterval(revealTimer);
		if (animate && points.length > 1) {
			let shown = 0;
			const step = Math.max(40, Math.round(1000 / points.length));
			const tick = () => {
				shown += 1;
				orientationChart?.setOption(orientationOption(shown), true);
				if (shown >= points.length) clearInterval(revealTimer);
			};
			tick();
			revealTimer = setInterval(tick, step);
		} else {
			orientationChart?.setOption(orientationOption(points.length), true);
		}
		sharesChart?.setOption(
			{
				grid: { left: 36, right: 8, top: 10, bottom: 22 },
				tooltip: {
					...TOOLTIP,
					trigger: 'axis',
					axisPointer: { type: 'none' }, // pas de trait pointillé au survol des barres
					formatter: (params: { dataIndex: number; marker: string; seriesName: string; value: number | null }[]) => {
						const p = points[params[0].dataIndex];
						const rows = params
							.filter((r) => !r.seriesName.startsWith('Abstention') && r.seriesName !== 'Pas de résultat' && r.value !== null && r.value !== undefined && (r.value as number) > 0)
							.map((r) => `<div>${r.marker}${esc(r.seriesName)} : <b>${formatPercent(r.value as number)}</b></div>`)
							.join('');
						return tooltipHeader(p) + note(p) + rows;
					}
				},
				xAxis: { type: 'category', data: years, axisTick: { show: false } },
				yAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)} %` } },
				series: [
					{
						// emplacement d'un scrutin sans résultat : barre vide en pointillés
						name: 'Pas de résultat',
						type: 'bar' as const,
						stack: 'parts',
						itemStyle: { color: '#f6f6f6', borderColor: '#bbb', borderType: 'dashed' as const, borderWidth: 1 },
						data: points.map((p) => (p.status === 'absent' ? 1 : 0))
					},
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

	<h3 class="section-title">Évolution de l'orientation des votes</h3>
	<div bind:this={orientationEl} class="chart orientation"></div>
	<div class="sides"><span>← Gauche</span><span>Droite →</span></div>
	{#if hasAbsent || hasUnscored}
		<ul class="marks">
			{#if hasAbsent}<li><span class="cross">×</span>Pas de résultat à ce scrutin (par exemple : élection pliée au premier tour)</li>{/if}
			{#if hasUnscored}<li><span class="ring"></span>Orientation moyenne non calculée (peu de voix étiquetées)</li>{/if}
		</ul>
	{/if}

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
	.marks {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin: 4px 0 0;
		padding: 0;
		list-style: none;
		font-size: 11px;
		color: var(--muted);
	}
	.marks li {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.cross {
		width: 10px;
		text-align: center;
		font-weight: 700;
		color: #999;
	}
	.ring {
		width: 8px;
		height: 8px;
		margin: 0 1px;
		border: 1.5px solid #999;
		border-radius: 50%;
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
