<script lang="ts">
	import MapView, { type Focus } from './MapView.svelte';
	import type { Level } from '../types';

	let {
		level,
		colors,
		selected = null,
		onselect,
		onzoom,
		focus = undefined
	}: {
		level: Level;
		colors: Record<string, string>;
		selected?: string | null;
		onselect: (id: string) => void;
		onzoom: (id: string) => void;
		focus?: Focus;
	} = $props();
</script>

<MapView {level} {colors} {selected} {onselect} {onzoom} {focus} />
