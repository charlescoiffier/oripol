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
		selected = null,
		onselect,
		onzoom,
		onclear,
		focus = undefined
	}: {
		level: Level;
		colors: Record<string, string>;
		selected?: string | null;
		onselect: (id: string) => void;
		onzoom: (id: string) => void;
		onclear: () => void;
		focus?: Focus;
	} = $props();

	const LAYERS = ['regions', 'departements', 'communes'] as const;
	// métropole + encart outre-mer en bas à gauche
	const HOME: Bounds = [-5.8, 37.2, 9.9, 51.3];
	const SEA = '#d3dde8';

	let container: HTMLDivElement;
	let map: import('maplibre-gl').Map | undefined;
	let ready = $state(false);
	// niveau lu par les écouteurs de la carte (qui ne suivent pas la réactivité)
	let levelRef: Level = 'departements';
	$effect(() => {
		levelRef = level;
	});
	let tip = $state<{ x: number; y: number; text: string } | null>(null);

	onMount(() => {
		const maplibregl = setupMaplibre();
		const m = new maplibregl.Map({
			container,
			style: { version: 8, sources: {}, layers: [{ id: 'bg', type: 'background', paint: { 'background-color': SEA } }] },
			bounds: HOME,
			fitBoundsOptions: { padding: 20 },
			maxZoom: 11,
			doubleClickZoom: false, // le double clic zoome sur l'emprise du territoire
			attributionControl: false,
			canvasContextAttributes: { preserveDrawingBuffer: true } // nécessaire à l'export de la carte en image
		});
		map = m;
		if (import.meta.env.DEV) (window as unknown as { __map: unknown }).__map = m;
		m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
		m.on('load', () => {
			m.addSource('contours', { type: 'vector', url: `pmtiles://${TILES_URL}` });
			// cadres de l'encart outre-mer, sous les territoires
			m.addLayer({ id: 'inset-fill', type: 'fill', source: 'contours', 'source-layer': 'inset', paint: { 'fill-color': '#e9eff6' } });
			m.addLayer({
				id: 'inset-line',
				type: 'line',
				source: 'contours',
				'source-layer': 'inset',
				paint: { 'line-color': '#9db0c5', 'line-width': 1 }
			});
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
				m.on('click', `${l}-fill`, (e: { features?: { properties?: Record<string, unknown> }[] }) => {
					const id = e.features?.[0]?.properties?.id;
					if (typeof id === 'string') onselect(id);
				});
				m.on('dblclick', `${l}-fill`, (e: { features?: { properties?: Record<string, unknown> }[] }) => {
					const id = e.features?.[0]?.properties?.id;
					if (typeof id === 'string') onzoom(id);
				});
			}
			// clic dans la mer (hors de tout territoire) : on quitte la sélection
			m.on('click', (e: { point: { x: number; y: number } }) => {
				const layers = LAYERS.map((l) => `${l}-fill`).filter((id) => m.getLayoutProperty(id, 'visibility') !== 'none');
				if (!m.queryRenderedFeatures([e.point.x, e.point.y], { layers }).length) onclear();
			});
			// contour du territoire sélectionné : un filtre par couche, toujours au-dessus
			for (const l of LAYERS) {
				m.addLayer({
					id: `${l}-selected`,
					type: 'line',
					source: 'contours',
					'source-layer': l,
					filter: ['==', ['get', 'id'], ''],
					layout: { 'line-join': 'round' },
					paint: { 'line-color': '#4a4f57', 'line-width': 1.4 }
				});
			}
			// info-bulle au survol : nom du territoire (utile pour reconnaître les cadres d'outre-mer)
			m.on('mousemove', (e: { point: { x: number; y: number } }) => {
				const f = m.queryRenderedFeatures([e.point.x, e.point.y], {
					layers: ['communes-fill', 'departements-fill', 'regions-fill', 'inset-fill'].filter((id) => m.getLayoutProperty(id, 'visibility') !== 'none')
				})[0];
				const name = f?.properties?.name;
				m.getCanvas().style.cursor = f && f.layer.id !== 'inset-fill' ? 'pointer' : '';
				// au niveau Pays, la carte n'a qu'un territoire : la France
				tip = typeof name === 'string' ? { x: e.point.x, y: e.point.y, text: levelRef === 'pays' ? 'France' : name } : null;
			});
			m.on('mouseout', () => (tip = null));
			ready = true;
		});
		// le conteneur change de taille quand un panneau latéral se rabat
		const ro = new ResizeObserver(() => m.resize());
		ro.observe(container);
		return () => {
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
			departements: level === 'departements' || level === 'communes',
			communes: level === 'communes'
		};
		for (const l of LAYERS) {
			m.setLayoutProperty(`${l}-fill`, 'visibility', fillShown[l] ? 'visible' : 'none');
			m.setLayoutProperty(`${l}-line`, 'visibility', lineShown[l] ? 'visible' : 'none');
		}
		// au niveau communes, les limites départementales (blanches, comme au niveau Départements) servent de
		// repère à petite échelle, puis s'effacent dès que les communes apparaissent
		m.setPaintProperty(
			'departements-line',
			'line-opacity',
			level === 'communes' ? ['interpolate', ['linear'], ['zoom'], 5.5, 1, 6.5, 0] : 1
		);

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

	// focus visuel : contour noir autour du territoire sélectionné
	$effect(() => {
		if (!ready || !map) return;
		for (const l of LAYERS) map.setFilter(`${l}-selected`, ['==', ['get', 'id'], selected ?? '']);
		for (const l of LAYERS) map.moveLayer(`${l}-selected`);
	});

	/**
	 * Image de la carte, cadrée sur `bounds` si fourni (la vue de l'utilisateur est ensuite restaurée).
	 */
	export async function capture(bounds?: Bounds): Promise<HTMLCanvasElement | null> {
		const m = map;
		if (!m || !ready) return null;
		const view = { center: m.getCenter(), zoom: m.getZoom(), bearing: m.getBearing(), pitch: m.getPitch() };
		const settled = (event: 'idle' | 'render') =>
			new Promise<void>((resolve) => {
				const timer = setTimeout(resolve, 8000); // une tuile bloquée ne doit pas bloquer l'export
				m.once(event, () => {
					clearTimeout(timer);
					resolve();
				});
			});
		if (bounds) {
			const idle = settled('idle');
			m.fitBounds(bounds, { padding: 40, duration: 0, maxZoom: 11 });
			await idle;
		}
		const rendered = settled('render');
		m.triggerRepaint();
		await rendered;
		const src = m.getCanvas();
		const out = document.createElement('canvas');
		out.width = src.width;
		out.height = src.height;
		out.getContext('2d')?.drawImage(src, 0, 0);
		if (bounds) m.jumpTo(view);
		return out;
	}

	$effect(() => {
		if (!ready || !map || !focus) return;
		map.fitBounds(focus.bounds, { padding: 70, duration: 700, maxZoom: 11 });
	});
</script>

<div bind:this={container} class="map"></div>
{#if tip}
	<div class="tip" style="left:{tip.x + 12}px; top:{tip.y + 12}px">{tip.text}</div>
{/if}

<style>
	.map {
		position: absolute;
		inset: 0;
	}
	.tip {
		position: absolute;
		z-index: 6;
		max-width: 220px;
		padding: 3px 7px;
		border-radius: 4px;
		background: rgba(32, 32, 32, 0.88);
		color: #fff;
		font-size: 12px;
		pointer-events: none;
	}
</style>
