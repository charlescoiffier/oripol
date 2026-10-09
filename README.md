# Oripol

Une application web qui montre comment un territoire français (commune, département, région, pays) se déplace politiquement d'une élection à l'autre, à partir des résultats officiels.

**Lancer l'application : `./start.sh`**

Aucun compte, aucun serveur applicatif : le site est statique et tout le calcul se fait dans le navigateur.

## Aperçu

| Départements, présidentielle 2022 | Recherche d'une commune, avec zoom | Principe de calcul et sources |
|---|---|---|
| ![Carte des départements, encart outre-mer et fiche du Rhône](docs/images/apercu-departements.jpg) | ![Lyon sélectionnée depuis la recherche](docs/images/recherche-commune.jpg) | ![Fenêtre À propos](docs/images/a-propos.jpg) |

---

# Pour tout le monde

## Le projet en bref

Oripol colore une carte de France selon l'orientation du vote (de la gauche à la droite) pour chaque élection, et trace l'évolution d'un territoire dans le temps. Cette version couvre le 1er tour des élections présidentielles de 2002 à 2022, pour **les 35 000 communes**, les départements, les régions, l'outre-mer et les Français établis hors de France.

Le classement des candidats par famille politique est proposé par défaut, mais chacun peut le modifier.

## Utiliser la carte

1. Choisir une **élection** dans le panneau de gauche.
2. Choisir un **niveau** : Pays, Régions, Départements ou Communes. Au niveau Communes, il faut zoomer pour distinguer les communes.
3. Cliquer sur un territoire, ou le chercher dans le panneau de droite (la liste se réduit pendant la frappe). Choisir un résultat le valide, bascule sur le niveau qui lui correspond et zoome dessus.
4. Lire sa fiche : **évolution de l'orientation du vote** depuis 2002, puis **répartition des votes** par famille, avec l'abstention.

Dans la fiche, les années sont empilées (2002 en bas, 2022 en haut) et la courbe se place de part et d'autre de la ligne médiane : la gauche à gauche, la droite à droite.

L'encart **Outre-mer**, en bas à gauche de la carte, montre les uns sous les autres la Guadeloupe, la Martinique, la Guyane, La Réunion, Mayotte, Saint-Pierre-et-Miquelon, Saint-Martin et Saint-Barthélemy, la Polynésie française, la Nouvelle-Calédonie et Wallis-et-Futuna, colorés comme la carte principale ; un clic sélectionne le territoire. Les deux panneaux latéraux se replient avec les flèches `‹` et `›`.

## Comprendre le score

- Chaque candidat est rattaché à une famille : extrême gauche, gauche, centre, droite, extrême droite, divers, régionalistes. Les écologistes (EELV et prédécesseurs) sont classés à gauche par défaut.
- Chaque famille occupe une position sur un axe de `-2` (extrême gauche) à `+2` (extrême droite). Les signes servent seulement à orienter l'axe, ils n'ont aucune valeur de jugement.
- Le **score** d'un territoire est la somme, sur les familles placées sur l'axe, de leur part des suffrages exprimés multipliée par leur position. Les familles hors axe (divers, régionalistes) diluent le score mais apparaissent dans la répartition des votes.
- La couleur de la carte sature à `±0,6` et monte vite aux faibles écarts : un territoire fortement orienté n'a pas besoin d'atteindre `±2`, et un territoire peu orienté reste nettement coloré. Un territoire sans donnée est gris foncé.

## Ajuster le classement

Le classement n'est qu'une proposition. Dans le panneau de gauche, on peut :

- déplacer le curseur d'une famille, ou la sortir de l'axe en décochant sa case ;
- rattacher un candidat à une autre famille (section « Rattachement des candidats ») ;
- revenir au classement d'origine avec « Réinitialiser ».

La carte et les courbes se recalculent aussitôt. L'adresse de la page conserve tous les réglages : il suffit de la copier pour partager une vue.

## Limites des données

- Les communes fusionnées sont regroupées dans la commune actuelle (découpage 2026).
- L'abstention, les blancs et les nuls sont rapportés aux inscrits.
- Un territoire sans donnée apparaît en gris, jamais comme « centre ».
- Le jeu source est incomplet pour deux scrutins : en 2002 il omet Mayotte, les collectivités d'outre-mer et les Français de l'étranger ; en 2007, les collectivités d'outre-mer et les Français de l'étranger. Le total « Pays » de ces deux années est donc un peu inférieur au résultat officiel.
- Pas encore de législatives, municipales ni départementales.

---

# Pour les développeurs

## Démarrage

Prérequis : [uv](https://docs.astral.sh/uv/), Node.js et [tippecanoe](https://github.com/felt/tippecanoe) (`brew install uv tippecanoe`).

```bash
./start.sh        # génère les données si besoin, lance le serveur et ouvre la page
./build-data.sh   # (re)génère seulement les données : ~240 Mo téléchargés la première fois
```

Les données générées (`web/static/data/`) et les sources téléchargées (`etl/data/`) ne sont pas versionnées : tout ce qui peut être régénéré est exclu du dépôt.

Avec Node 23.5, `npm install` doit recevoir `--engine-strict=false` (c'est ce que fait `start.sh`).

## Architecture

```
sources officielles (parquet, CSV)
  → ETL Python (polars) : codes communes, fusions, rattachement candidat → famille, contrôles
  → JSON compacts par élection + contours PMTiles
  → site statique SvelteKit : MapLibre (cartes) + ECharts (courbes), score calculé dans le navigateur
```

- **ETL** (`etl/`) : lit les fichiers, résout les fusions de communes avec l'historique des mouvements du COG, rattache les candidats à une famille (`etl/mappings/presidentielle.yaml`), agrège commune → département → région → pays, puis **échoue sans rien écrire** si la somme des voix d'une commune diffère des exprimés ou si un candidat n'a pas de famille.
- **Site** (`web/`) : charge les résultats bruts et recalcule le score à chaque réglage, ce qui rend le classement ajustable sans serveur. Les contours sont des tuiles PMTiles ; la couche des 35 000 communes n'est embarquée qu'à partir du zoom 6.
- **Territoires** : identifiants `FR`, `REG-<code>`, `DEP-<code>` et `COM-<code INSEE>`. Les collectivités d'outre-mer sont à la fois leur propre département et leur propre région ; les Français de l'étranger forment le département fictif `DEP-ZZ`, sans carte.

## Sources de données

| Donnée | Source | Usage |
|---|---|---|
| Résultats par bureau de vote | [Données des élections agrégées](https://www.data.gouv.fr/datasets/6481e741d4cf002ec0efec9d) (data.gouv.fr, d'après le ministère de l'Intérieur) | Résultats, agrégés par commune |
| Fusions de communes, outre-mer | Code officiel géographique de l'Insee, millésime 2026 | Résolution des codes, collectivités d'outre-mer |
| Régions et départements de métropole | [france-geojson](https://github.com/gregoiredavid/france-geojson) (d'après IGN Admin Express) | Contours |
| Communes, départements et régions d'outre-mer | API [Découpage administratif](https://geo.api.gouv.fr) | Contours (les DOM sont fusionnés depuis leurs communes) |

## Paramètres d'URL

| Paramètre | Rôle | Exemple |
|---|---|---|
| `e` | Élection | `e=pres-2022-1` |
| `t` | Territoire sélectionné | `t=DEP-69`, `t=COM-69123`, `t=FR` |
| `v` | Niveau (`pays`, `regions`, `departements`, `communes`) ; `departements` par défaut | `v=communes` |
| `p` | Positions modifiées, `famille~valeur` séparés par des virgules (`x` = hors axe) | `p=gauche~-0.5,divers~x` |
| `l` | Rattachements modifiés, `liste~famille` séparés par des virgules | `l=pres-2022-1.MACRON~droite` |

Les paramètres invalides sont ignorés sans erreur.

## Structure du dépôt

| Dossier | Contenu |
|---|---|
| `etl/src/oripol_etl/` | Pipeline : `cog`, `geo`, `ministry`, `families`, `aggregate`, `validate`, `export` |
| `etl/scripts/` | Téléchargement des sources et construction des contours |
| `etl/mappings/` | Familles et rattachement des candidats (données à relire avant publication) |
| `web/src/lib/` | Logique pure (`score`, `series`, `search`, `url-state`) et composants Svelte |
| `docs/` | Spécification, plan d'implémentation et captures d'écran |

## Tests

```bash
uv run --project etl pytest etl/tests   # ETL : résolution des fusions, agrégation, contrôles, export
npm --prefix web test                    # logique du site : score, URL, couleurs, recherche, séries
npm --prefix web run check               # vérification des types
```
