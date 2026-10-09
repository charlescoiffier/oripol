<script lang="ts">
	import { BASE } from '../../lib/paths';
</script>

<svelte:head><title>Sources – Oripol</title></svelte:head>
<main style="max-width: 46rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5">
	<p><a href="{BASE}/">← Retour à la carte</a></p>
	<h1>Sources</h1>
	<ul>
		<li><a href="https://www.data.gouv.fr/datasets/6481e741d4cf002ec0efec9d">Données des élections agrégées</a> (data.gouv.fr, d'après les fichiers du ministère de l'Intérieur) : résultats par bureau de vote, agrégés par commune.</li>
		<li>Contours : <a href="https://github.com/gregoiredavid/france-geojson">france-geojson</a> (régions et départements, d'après IGN Admin Express) et API <a href="https://geo.api.gouv.fr">Découpage administratif</a> (communes).</li>
		<li><a href="https://www.insee.fr/fr/statistiques/3698339">Historique des populations communales 1876-2023</a> (Insee) : sélection des communes ayant dépassé 30 000 habitants.</li>
		<li>Code officiel géographique (Insee, millésime 2026) : fusions de communes, préfectures et sous-préfectures.</li>
	</ul>
	<h2>Limites connues</h2>
	<ul>
		<li>Les communes fusionnées sont regroupées dans la commune actuelle.</li>
		<li>« France » exclut les Français établis hors de France et les collectivités d'outre-mer.</li>
		<li>Seule la présidentielle (1er tour, 2002-2022) est disponible dans cette version.</li>
	</ul>
</main>
