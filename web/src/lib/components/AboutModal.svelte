<script lang="ts">
	let { open = $bindable(false) }: { open: boolean } = $props();
	let dialog: HTMLDialogElement;

	$effect(() => {
		if (!dialog) return;
		if (open && !dialog.open) dialog.showModal();
		if (!open && dialog.open) dialog.close();
	});
</script>

<dialog bind:this={dialog} onclose={() => (open = false)} onclick={(e) => e.target === dialog && (open = false)}>
	<div class="box">
		<header>
			<h2>À propos d'Oripol</h2>
			<button class="icon-btn" type="button" aria-label="Fermer" onclick={() => (open = false)}>✕</button>
		</header>

		<section>
			<h3>Deux modes d'affichage</h3>
			<ul>
				<li>
					<strong>Classique</strong> : le panneau de droite détaille les résultats, avec le nombre de voix, le
					pourcentage des exprimés et l'abstention. Dans une commune, chaque liste ou candidat apparaît séparément,
					avec son nom (candidat ou tête de liste, à défaut le nom de la liste) pour les législatives, les
					régionales, les municipales et, pour les présidentielles, le candidat. La commune prend la couleur de
					la famille de la liste arrivée en tête. Pour un département, une région ou le pays, les voix sont
					regroupées par nuance politique : ils prennent la couleur de la nuance qui arrive en tête, avec un nom
					quand une seule personne la porte. Les voix sans étiquette ne comptent pas pour la couleur</li>
				<li>
					<strong>Évolution</strong> : la carte est colorée selon l'orientation moyenne des votes (de la gauche à la
					droite), et le panneau de droite montre sa trajectoire d'un scrutin à l'autre.
				</li>
			</ul>
		</section>

		<section>
			<h3>Principe de calcul</h3>
			<p>
				Chaque candidat (présidentielles) ou chaque nuance politique du ministère de l'Intérieur (autres scrutins) est
				rattaché à une famille politique : extrême gauche, gauche, centre, droite,
				extrême droite, divers et régionalistes. Les écologistes (EELV et prédécesseurs) sont classés à
				gauche par défaut.
			</p>
			<p>
				Chaque famille a une position sur un axe de −2 (extrême gauche) à +2 (extrême droite). L'<strong>orientation
				moyenne</strong> d'un territoire est la position moyenne de ses suffrages : la somme, sur les familles placées
				sur l'axe, de leur part des suffrages exprimés multipliée par leur position. Les familles divers et
				régionalistes sont placées par défaut à 0, au milieu de l'axe : leurs voix pèsent comme celles du centre et
				apparaissent dans la répartition des votes. Les signes négatifs ou positifs n'ont aucune
				valeur de jugement : ils servent seulement à orienter l'axe. Dans les graphiques, la moyenne est traduite en
				nuance : gauche, centre gauche, centre, centre droit, droite.
			</p>
			<p>
				Ce classement est discutable : vous pouvez modifier la position de chaque famille et le rattachement
				de chaque candidat. Le lien de la page conserve vos réglages.
			</p>
			<p>
				<strong>Attention : les tendances dépendent beaucoup du classement.</strong> Par défaut, la France
				insoumise est rangée à gauche (et non à l'extrême gauche, sauf aux municipales de 2026) et Emmanuel Macron au centre. Avec ces choix, la
				droite et l'extrême droite semblent progresser de 2002 à 2022, alors que la part de la gauche recule et
				que le centre double. Rattachez ces candidats autrement pour voir l'effet.
			</p>
		</section>

		<section>
			<h3>Méthodologie</h3>
			<ul>
				<li>
					Les résultats couvrent les présidentielles, les législatives, les européennes, les régionales, les
					départementales, les cantonales et les municipales, commune par commune (1er et 2d tours quand il y
					en a).
				</li>
				<li>
					Au 2d tour, seules les communes où un second tour a eu lieu ont des résultats. Les cantonales et
					départementales ne renouvellent qu'une partie des cantons à chaque scrutin : le reste de la carte est
					en gris.
				</li>
				<li>Les communes fusionnées sont regroupées dans la commune actuelle (découpage 2026).</li>
				<li>L'abstention et les blancs et nuls sont rapportés aux inscrits.</li>
				<li>Un territoire sans donnée apparaît en gris, jamais comme « centre ».</li>
				<li>
					<strong>Municipales :</strong> seules les communes d'une certaine taille ont des étiquettes politiques
					(nuances) : environ 3 500 habitants et plus en 2008 et en 2026, environ 1 000 habitants et plus en 2014 et
					en 2020. Les voix sans étiquette sont affichées « Non classé » et ne comptent pas dans l'orientation, qui
					n'est calculée que si au moins 30 % des voix sont étiquetées. Les départements, les régions et le pays
					reflètent donc surtout les communes étiquetées.
				</li>
				<li>Les comparaisons se font entre scrutins de même nature.</li>
				<li>
					« Pays » regroupe tous les territoires, y compris l'outre-mer et les Français établis hors de
					France. En 2002, le jeu source omet Mayotte, les collectivités d'outre-mer et les Français de
					l'étranger ; en 2007, les collectivités d'outre-mer et les Français de l'étranger : les totaux
					nationaux de ces deux années sont donc un peu inférieurs aux résultats officiels.
				</li>
			</ul>
		</section>

		<section>
			<h3>Partager, exporter, accessibilité</h3>
			<ul>
				<li>
					« Copier le lien » conserve l'élection, le territoire, le mode, le niveau et vos réglages de
					classement.
				</li>
				<li>
					« Image PNG » exporte la carte cadrée sur le territoire sélectionné, sa légende et les graphiques de
					votre choix ; « PDF A4 » rassemble le tout sur une page.
				</li>
				<li>
					La case « Palette adaptée aux daltoniens » remplace le rouge par de l'orange et recolore les familles
					avec des teintes distinguables par les daltoniens.
				</li>
			</ul>
		</section>

		<section>
			<h3>Sources</h3>
			<ul>
				<li>
					<a href="https://www.data.gouv.fr/datasets/6481e741d4cf002ec0efec9d" target="_blank" rel="noreferrer">Données des élections agrégées</a>
					(data.gouv.fr, d'après le ministère de l'Intérieur) : résultats par bureau de vote, agrégés par commune.
				</li>
				<li>
					Contours : <a href="https://github.com/gregoiredavid/france-geojson" target="_blank" rel="noreferrer">france-geojson</a>
					(régions et départements, d'après IGN Admin Express) et l'API
					<a href="https://geo.api.gouv.fr" target="_blank" rel="noreferrer">Découpage administratif</a> (communes).
				</li>
				<li>
					Nuances politiques :
					<a href="https://www.data.gouv.fr/datasets/6481e741d4cf002ec0efec9d" target="_blank" rel="noreferrer">dictionnaire des nuances</a>
					du ministère de l'Intérieur (blocs de la circulaire de 2026), complété à la main pour les codes anciens.
				</li>
				<li>Code officiel géographique de l'Insee (millésime 2026) : fusions de communes, collectivités d'outre-mer.</li>
			</ul>
		</section>
	</div>
</dialog>

<style>
	dialog {
		width: min(640px, calc(100vw - 32px));
		max-height: calc(100vh - 48px);
		padding: 0;
		border: 0;
		border-radius: 10px;
		box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
	}
	dialog::backdrop {
		background: rgba(0, 0, 0, 0.35);
	}
	.box {
		padding: 16px 20px 20px;
		line-height: 1.5;
	}
	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 4px;
	}
	h2 {
		font-size: 16px;
	}
	h3 {
		margin: 14px 0 4px;
		font-size: 13px;
		color: var(--accent);
	}
	p,
	ul {
		margin: 4px 0;
	}
	ul {
		padding-left: 18px;
	}
	a {
		color: var(--accent);
	}
</style>
