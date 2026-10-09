<script lang="ts">
	import maplibregl from 'maplibre-gl/dist/maplibre-gl-csp';
	import workerUrl from 'maplibre-gl/dist/maplibre-gl-csp-worker?url';
	import 'maplibre-gl/dist/maplibre-gl.css';
	import { PMTiles, Protocol } from 'pmtiles';
	import { onMount } from 'svelte';
	import { BASE } from '../paths';
	import { NO_DATA_COLOR } from '../color';
	import type { Level } from '../types';

	let {
		level,
		colors,
		onselect
	}: { level: Level; colors: Record<string, string>; onselect: (id: string) => void } = $props();

	maplibregl.setWorkerUrl(workerUrl);

	const LAYERS = ['regions', 'departements', 'communes'] as const;
	const ZONES: [string, [[number, number], [number, number]]][] = [
		['France métropolitaine', [[-5.5, 41.2], [9.8, 51.2]]],
		['Antilles', [[-63.3, 14.3], [-60.7, 18.2]]],
		['Guyane', [[-54.7, 2.0], [-51.5, 5.9]]],
		['La Réunion', [[55.1, -21.5], [55.9, -20.8]]],
		['Mayotte', [[44.9, -13.1], [45.4, -12.6]]],
		['Saint-Pierre-et-Miquelon', [[-56.5, 46.7], [-56.0, 47.2]]],
		['Polynésie française', [[-154, -27.8], [-134, -7.5]]],
		['Nouvelle-Calédonie', [[163.5, -23], [168.5, -19.5]]],
		['Wallis-et-Futuna', [[-178.3, -14.5], [-176, -13]]]
	];

	function goTo(i: number) {
		map?.fitBounds(ZONES[i][1], { padding: 40, duration: 700, maxZoom: 10 });
	}
	let container: HTMLDivElement;
	let map: maplibregl.Map | undefined;
	let ready = $state(false);

	onMount(() => {
		const tilesUrl = `${BASE}/data/contours.pmtiles`; // chemin relatif à l'origine : les URL absolues sont mal analysées par le protocole
		const protocol = new Protocol();
		protocol.add(new PMTiles(tilesUrl));
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
			maxZoom: 11,
			attributionControl: false
		});
		map = m;
		if (import.meta.env.DEV) (window as unknown as { __map: unknown }).__map = m;
		m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
		m.on('load', () => {
			m.addSource('contours', {
				type: 'vector',
				url: `pmtiles://${tilesUrl}`
			});
			for (const l of LAYERS) {
				m.addLayer({
					id: `${l}-fill`,
					type: 'fill',
					source: 'contours',
					'source-layer': l,
					...(l === 'communes' ? { minzoom: 6 } : {}),
					paint: { 'fill-color': NO_DATA_COLOR, 'fill-opacity': 0.95 }
				});
				m.addLayer({
					id: `${l}-line`,
					type: 'line',
					source: 'contours',
					'source-layer': l,
					...(l === 'communes' ? { minzoom: 6 } : {}),
					paint: {
						'line-color': '#ffffff',
						'line-width': l === 'communes' ? 0.4 : 0.7,
						// les 35 000 communes ne se distinguent qu'en zoomant
						'line-opacity': l === 'communes' ? ['interpolate', ['linear'], ['zoom'], 6.5, 0, 8, 1] : 1
					}
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
		// le conteneur change de taille quand un panneau latéral se rabat
		const ro = new ResizeObserver(() => m.resize());
		ro.observe(container);
		return () => {
			ro.disconnect();
			m.remove();
			maplibregl.removeProtocol('pmtiles');
		};
	});

	$effect(() => {
		if (!ready || !map) return;
		const m = map;
		const fillShown: Record<string, boolean> = {
			regions: level === 'regions',
			departements: level !== 'regions',
			communes: level === 'communes'
		};
		const lineShown: Record<string, boolean> = {
			regions: level === 'regions',
			departements: level !== 'regions' && level !== 'pays',
			communes: level === 'communes'
		};
		for (const l of LAYERS) {
			m.setLayoutProperty(`${l}-fill`, 'visibility', fillShown[l] ? 'visible' : 'none');
			m.setLayoutProperty(`${l}-line`, 'visibility', lineShown[l] ? 'visible' : 'none');
		}
		// au niveau communes, les limites départementales restent visibles par-dessus
		m.setPaintProperty('departements-line', 'line-color', level === 'communes' ? '#8a8f98' : '#ffffff');
		m.setPaintProperty('departements-line', 'line-width', level === 'communes' ? 0.8 : 0.7);
		if (level === 'communes') m.moveLayer('departements-line');

		// regroupe les identifiants par couleur : une expression « match » compacte même à 35 000 communes
		const groups = new Map<string, string[]>();
		for (const [id, color] of Object.entries(colors)) {
			const g = groups.get(color);
			if (g) g.push(id);
			else groups.set(color, [id]);
		}
		const expr: unknown[] = ['match', ['get', 'id']];
		for (const [color, ids] of groups) expr.push(ids, color);
		expr.push(NO_DATA_COLOR);
		for (const l of LAYERS) {
			m.setPaintProperty(`${l}-fill`, 'fill-color', (groups.size ? expr : NO_DATA_COLOR) as never);
		}
	});
</script>

<div bind:this={container} class="map"></div>
<select class="zones" aria-label="Aller à une zone" onchange={(e) => {
	goTo(Number(e.currentTarget.value));
	e.currentTarget.value = '';
}}>
	<option value="" selected disabled>Aller à…</option>
	{#each ZONES as [label], i (label)}
		<option value={i}>{label}</option>
	{/each}
</select>

<style>
	.map {
		position: absolute;
		inset: 0;
	}
	.zones {
		position: absolute;
		left: 10px;
		bottom: 10px;
		z-index: 4;
		width: 150px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
	}
</style>
