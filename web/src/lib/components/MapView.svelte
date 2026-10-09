<script lang="ts">
	import { onMount } from 'svelte';
	import { NO_DATA_COLOR } from '../color';
	import { TILES_URL, setupMaplibre } from '../maplibre';
	import type { Level } from '../types';

	export type Bounds = [number, number, number, number]; // ouest, sud, est, nord
	export type Focus = { bounds: Bounds };

	let {
		level,
		colors,
		onselect,
		bounds = undefined,
		center = [2.5, 46.6],
		zoom = 4.8,
		interactive = true,
		focus = undefined
	}: {
		level: Level;
		colors: Record<string, string>;
		onselect: (id: string) => void;
		bounds?: Bounds;
		center?: [number, number];
		zoom?: number;
		interactive?: boolean;
		focus?: Focus;
	} = $props();

	const LAYERS = ['regions', 'departements', 'communes'] as const;
	let container: HTMLDivElement;
	let map: ReturnType<typeof createMap> | undefined;
	let ready = $state(false);

	function createMap() {
		const maplibregl = setupMaplibre();
		return new maplibregl.Map({
			container,
			style: {
				version: 8,
				sources: {},
				layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#d3dde8' } }]
			},
			...(bounds ? { bounds, fitBoundsOptions: { padding: 6 } } : { center, zoom }),
			maxZoom: 11,
			interactive,
			attributionControl: false
		});
	}

	function visibleFills(l: Level): string[] {
		return l === 'regions' ? ['regions-fill'] : l === 'communes' ? ['communes-fill', 'departements-fill'] : ['departements-fill'];
	}

	onMount(() => {
		const maplibregl = setupMaplibre();
		const m = createMap();
		map = m;
		if (import.meta.env.DEV && interactive) (window as unknown as { __map: unknown }).__map = m;
		if (interactive) m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
		m.on('load', () => {
			m.addSource('contours', { type: 'vector', url: `pmtiles://${TILES_URL}` });
			for (const l of LAYERS) {
				const minzoom = l === 'communes' ? { minzoom: 6 } : {};
				m.addLayer({
					id: `${l}-fill`,
					type: 'fill',
					source: 'contours',
					'source-layer': l,
					...minzoom,
					paint: { 'fill-color': NO_DATA_COLOR, 'fill-opacity': 0.95 }
				});
				m.addLayer({
					id: `${l}-line`,
					type: 'line',
					source: 'contours',
					'source-layer': l,
					...minzoom,
					paint: {
						'line-color': '#ffffff',
						'line-width': l === 'communes' ? 0.4 : 0.7,
						// les 35 000 communes ne se distinguent qu'en zoomant
						'line-opacity': l === 'communes' ? ['interpolate', ['linear'], ['zoom'], 6.5, 0, 8, 1] : 1
					}
				});
				if (interactive) {
					m.on('click', `${l}-fill`, (e: { features?: { properties?: Record<string, unknown> }[] }) => {
						const id = e.features?.[0]?.properties?.id;
						if (typeof id === 'string') onselect(id);
					});
					m.on('mouseenter', `${l}-fill`, () => (m.getCanvas().style.cursor = 'pointer'));
					m.on('mouseleave', `${l}-fill`, () => (m.getCanvas().style.cursor = ''));
				}
			}
			ready = true;
		});
		// les encarts ne sont pas interactifs : on retrouve le territoire cliqué à la main
		const onBoxClick = (e: MouseEvent) => {
			if (interactive || !ready) return;
			const rect = container.getBoundingClientRect();
			const f = m.queryRenderedFeatures([e.clientX - rect.left, e.clientY - rect.top], { layers: visibleFills(level) });
			const id = f[0]?.properties?.id;
			if (typeof id === 'string') onselect(id);
		};
		container.addEventListener('click', onBoxClick);
		// le conteneur change de taille quand un panneau latéral se rabat
		const ro = new ResizeObserver(() => m.resize());
		ro.observe(container);
		return () => {
			container.removeEventListener('click', onBoxClick);
			ro.disconnect();
			m.remove();
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

	$effect(() => {
		if (!ready || !map || !focus) return;
		map.fitBounds(focus.bounds, { padding: 70, duration: 700, maxZoom: 11 });
	});
</script>

<div bind:this={container} class="map"></div>

<style>
	.map {
		position: absolute;
		inset: 0;
	}
</style>
