<script lang="ts">
	import { BASE } from '../../lib/paths';
</script>

<svelte:head><title>Méthodologie – Oripol</title></svelte:head>
<main style="max-width: 46rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5">
	<p><a href="{BASE}/">← Retour à la carte</a></p>
	<h1>Méthodologie</h1>
	<p>Chaque candidat est rattaché à une famille politique (extrême gauche, gauche, centre, droite, extrême droite, divers, régionalistes). Les écologistes (EELV et prédécesseurs) sont classés à gauche par défaut.</p>
	<p>Chaque famille a une position sur un axe de −2 (extrême gauche) à +2 (extrême droite). Le <strong>score</strong> d'un territoire est la somme, sur les familles placées sur l'axe, de leur part des suffrages exprimés multipliée par leur position. Les familles hors axe diluent le score mais figurent dans les parts affichées.</p>
	<p>Ce classement est discutable : vous pouvez modifier la position de chaque famille et le rattachement de chaque candidat ; le lien de la page conserve vos réglages.</p>
	<p>L'abstention est rapportée aux inscrits. Un territoire sans donnée n'est jamais affiché comme neutre : il apparaît en gris.</p>
	<p>Les comparaisons se font entre scrutins de même nature (ici : présidentielles, 1er tour).</p>
</main>
