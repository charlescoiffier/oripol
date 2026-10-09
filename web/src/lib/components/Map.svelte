<script lang="ts">
	import * as maplibregl from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';
	import { Protocol } from 'pmtiles';
	import { onMount } from 'svelte';
	import { BASE } from '../paths';
	import { NO_DATA_COLOR } from '../color';
	import type { Level } from '../types';

	let {
		level,
		colors,
		onselect
	}: { level: Level; colors: Record<string, string>; onselect: (id: string) => void } = $props();

	const LAYERS: Level[] = ['regions', 'departements', 'communes'];
	let container: HTMLDivElement;
	let map: maplibregl.Map | undefined;
	let ready = $state(false);

	onMount(() => {
		const protocol = new Protocol();
		maplibregl.addProtocol('pmtiles', protocol.tile);
		const m = new maplibregl.Map({
			container,
			style: {
				version: 8,
				sources: {},
				layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#eef1f4' } }]
			},
			center: [2.5, 46.6],
			zoom: 4.8,
			maxZoom: 11
		});
		map = m;
		m.addControl(new maplibregl.NavigationControl({ showCompass: false }));
		m.on('load', () => {
			m.addSource('contours', {
				type: 'vector',
				url: `pmtiles://${location.origin}${BASE}/data/contours.pmtiles`
			});
			for (const l of LAYERS) {
				m.addLayer({
					id: `${l}-fill`,
					type: 'fill',
					source: 'contours',
					'source-layer': l,
					paint: { 'fill-color': NO_DATA_COLOR, 'fill-opacity': 0.92 }
				});
				m.addLayer({
					id: `${l}-line`,
					type: 'line',
					source: 'contours',
					'source-layer': l,
					paint: { 'line-color': '#ffffff', 'line-width': 0.6 }
				});
				m.on('click', `${l}-fill`, (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
					const id = e.features?.[0]?.properties?.id;
					if (typeof id === 'string') onselect(id);
				});
				m.on('mouseenter', `${l}-fill`, () => (m.getCanvas().style.cursor = 'pointer'));
				m.on('mouseleave', `${l}-fill`, () => (m.getCanvas().style.cursor = ''));
			}
			ready = true;
		});
		return () => {
			m.remove();
			maplibregl.removeProtocol('pmtiles');
		};
	});

	$effect(() => {
		if (!ready || !map) return;
		const m = map;
		const shown: Record<string, boolean> = {
			regions: level === 'regions',
			// les communes s'affichent par-dessus les départements (fond neutre)
			departements: level === 'departements' || level === 'communes',
			communes: level === 'communes'
		};
		for (const l of LAYERS) {
			const v = shown[l] ? 'visible' : 'none';
			m.setLayoutProperty(`${l}-fill`, 'visibility', v);
			m.setLayoutProperty(`${l}-line`, 'visibility', v);
		}
		const entries = Object.entries(colors);
		const paint = (l: Level) => {
			if (level === 'communes' && l === 'departements') return NO_DATA_COLOR;
			if (!entries.length) return NO_DATA_COLOR;
			return ['match', ['get', 'id'], ...entries.flat(), NO_DATA_COLOR];
		};
		for (const l of LAYERS) m.setPaintProperty(`${l}-fill`, 'fill-color', paint(l) as never);
	});
</script>

<div bind:this={container} class="map"></div>

<style>
	.map {
		width: 100%;
		height: 100%;
		min-height: 420px;
	}
</style>
