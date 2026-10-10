<script lang="ts">
	import MapView, { type Bounds, type Focus } from './MapView.svelte';
	import type { Level } from '../types';

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

	let view: ReturnType<typeof MapView> & { capture: (b?: Bounds) => Promise<HTMLCanvasElement | null> };

	/** Image de la carte cadrée sur `bounds` (vue actuelle si absent). */
	export const capture = (bounds?: Bounds) => view.capture(bounds);
</script>

<MapView bind:this={view} {level} {colors} {selected} {onselect} {onzoom} {onclear} {focus} />
