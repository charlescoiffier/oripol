import maplibregl from 'maplibre-gl/dist/maplibre-gl-csp';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-csp-worker?url';
import 'maplibre-gl/dist/maplibre-gl.css';
import { PMTiles, Protocol } from 'pmtiles';
import { BASE } from './paths';

export const TILES_URL = `${BASE}/data/contours.pmtiles`; // chemin relatif à l'origine : les URL absolues sont mal analysées par le protocole

let ready = false;

/** Initialise MapLibre une seule fois (worker, protocole PMTiles), partagé par toutes les cartes. */
export function setupMaplibre() {
	if (!ready) {
		maplibregl.setWorkerUrl(workerUrl);
		const protocol = new Protocol();
		protocol.add(new PMTiles(TILES_URL));
		maplibregl.addProtocol('pmtiles', protocol.tile);
		ready = true;
	}
	return maplibregl;
}
