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
			<h3>Principe de calcul</h3>
			<p>
				Chaque candidat est rattaché à une famille politique : extrême gauche, gauche, centre, droite,
				extrême droite, divers et régionalistes. Les écologistes (EELV et prédécesseurs) sont classés à
				gauche par défaut.
			</p>
			<p>
				Chaque famille a une position sur un axe de −2 (extrême gauche) à +2 (extrême droite). Le
				<strong>score</strong> d'un territoire est la somme, sur les familles placées sur l'axe, de leur part
				des suffrages exprimés multipliée par leur position. Les familles hors axe diluent le score mais
				apparaissent dans la répartition des votes. Les signes négatifs ou positifs n'ont aucune valeur de
				jugement : ils servent seulement à orienter l'axe.
			</p>
			<p>
				Ce classement est discutable : vous pouvez modifier la position de chaque famille et le rattachement
				de chaque candidat. Le lien de la page conserve vos réglages.
			</p>
		</section>

		<section>
			<h3>Méthodologie</h3>
			<ul>
				<li>Les résultats sont ceux du 1er tour des élections présidentielles, de 2002 à 2022.</li>
				<li>Les communes fusionnées sont regroupées dans la commune actuelle (découpage 2026).</li>
				<li>L'abstention et les blancs et nuls sont rapportés aux inscrits.</li>
				<li>Un territoire sans donnée apparaît en gris, jamais comme « centre ».</li>
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
