# Oripol – Spécification de conception

Date : 2026-10-09 · Statut : brouillon à relire

## 1. Objectif
Application web publique permettant de visualiser l'évolution politique d'un territoire français (commune, département, région, pays) à partir des résultats officiels des élections présidentielles, législatives, municipales et départementales (ex-cantonales), sur la plus longue période exploitable sans numérisation d'archives. Le visiteur voit si un territoire se déplace vers l'extrême gauche, la gauche, le centre, la droite ou l'extrême droite, et peut ajuster le classement des partis.

Critères de succès :
- Un visiteur ouvre une carte, choisit une élection, voit les territoires colorés et la précision de la donnée.
- Il ouvre la fiche d'un territoire et lit sa trajectoire sur la période disponible.
- Il modifie le classement d'un parti : carte et courbes se recalculent immédiatement, et l'URL permet de partager le résultat.
- Chaque chiffre est rattaché à une source et à un niveau de précision.

## 2. Périmètre
Territoires :
- Pays, régions, départements (couverture complète).
- Communes cibles : communes ayant dépassé 30 000 habitants à un recensement (Insee 1876-2023) + préfectures et sous-préfectures (COG).
- Géographie de référence : **découpage communal actuel** ; les anciennes communes fusionnées sont regroupées dans la commune actuelle (validé).

Scrutins : présidentielles, législatives, municipales, départementales/cantonales. Régionales et européennes : phase 2, car elles aident à lire les tendances.

Hors périmètre : numérisation d'archives antérieures aux fichiers existants, comptes utilisateurs, bureaux de vote (extension possible plus tard), prédictions.

## 3. Sources de données
| Donnée | Source | Usage |
|---|---|---|
| Résultats 2002-2026 | data.gouv.fr « Données des élections agrégées » + jeux par scrutin du ministère de l'Intérieur | Résultats communaux (agrégés depuis les bureaux) |
| Municipales 2026 | data.gouv.fr « Elections municipales 2026 » | Idem |
| Résultats 1958-2012 | CDSP Sciences Po (législatives, présidentielles 1965-2012, régionales 1986-2010, cantonales 1988-2011) | Circonscription / canton / commune > 9 000 hab. selon l'année |
| Contours | IGN « Contours administratifs » | Cartes (généralisés, convertis en PMTiles) |
| Populations | Insee « Historique des populations communales 1876-2023 » | Sélection des communes cibles |
| Géographie | Insee COG + historique des mouvements de communes | Table de passage ancien code → commune actuelle |

Les jeux CDSP sont mis à disposition pour la recherche et l'enseignement et contiennent d'éventuelles erreurs : les conditions de réutilisation (licence ODbL sur data.gouv.fr, mention de citation du CDSP) doivent être reprises dans la page « Sources » du site. Les municipales avant 2001 sont à explorer dans la banque du CDSP ; en leur absence, elles sont exclues du MVP.

## 4. Précision des données (principe central)
Chaque couple (élection, territoire) porte un champ `precision` parmi `commune`, `circonscription`, `canton`, `departement`. Conséquences :
- 2002-2026 : précision commune pour toutes les communes cibles.
- Avant 2002 : commune seulement pour les communes > 9 000 habitants (années disponibles variables) ; sinon repli sur la circonscription, le canton ou le département, signalé visuellement (hachures + infobulle).
- La fiche territoire n'interpole jamais : un point sans donnée reste vide.
- La précision d'une donnée est toujours visible dans l'interface.

## 5. Modèle de données (PostgreSQL/PostGIS, source de vérité)
- `territoire(id, type, code_insee, nom, parent_id, geom)` – type : pays, région, département, commune ; version actuelle.
- `commune_historique(code_ancien, date_debut, date_fin, code_actuel)` – table de passage utilisée à l'ingestion.
- `population_commune(code_actuel, annee, population)` ; `commune_cible(code_actuel, motif)` – motif : seuil 30 000, préfecture, sous-préfecture.
- `election(id, type, annee, tour, date, source, granularite_source)`.
- `liste_candidat(id, election_id, libelle, nuance_source, famille_id)`.
- `resultat(election_id, territoire_id, liste_candidat_id, voix, precision)`.
- `participation(election_id, territoire_id, inscrits, votants, blancs, nuls, exprimes, precision)`.
- `famille(id, libelle, position_defaut)` ; `mapping_famille(clef_source, election_type, date_debut, date_fin, famille_id, justification)` – table datée, versionnée, avec justification et source de chaque rattachement.

Les agrégats département/région/pays sont calculés par l'ETL à partir des communes (2002+) ou des totaux officiels des fichiers CDSP, sans recalcul par échantillon.

## 6. Classement politique
Familles proposées (position par défaut sur l'axe) : extrême gauche (−2), gauche (−1), centre (0), droite (+1), extrême droite (+2), plus « divers » et « régionalistes » placées par défaut hors axe (affichées mais non comptées dans le score). Les écologistes ne forment pas une famille à part : Europe Écologie Les Verts (et ses prédécesseurs Les Verts, etc.) est classé à gauche par défaut (validé) ; les listes écologistes non rattachables à la gauche (ex. Génération Écologie, Mouvement écologiste indépendant) sont examinées au cas par cas dans `mapping_famille` avec justification. Le détail du rattachement de chaque parti/liste est un livrable de l'ETL (`mapping_famille`), à valider avant publication ; le défaut sera documenté et sourcé sur une page de méthodologie.

Score d'un territoire pour une élection : somme sur les familles placées sur l'axe de (part des suffrages exprimés de la famille × position). Le visiteur ajuste soit la position (curseur de −2 à +2) soit le rattachement famille d'un parti. Les parts de chaque famille, l'abstention (rapportée aux inscrits) et les blancs/nuls sont toujours affichés à côté du score, car un score élevé avec 60 % d'abstention ne signifie pas la même chose.

Comparaisons : une élection est comparée à la même catégorie de scrutin (présidentielle vs présidentielle, municipale vs municipale). Le glissement est la différence de score entre deux scrutins comparables. Les comparaisons inter-scrutins sont possibles mais accompagnées d'un avertissement.

## 7. Architecture
```
sources (CSV/XLSX/SHP)
  → ETL Python (DuckDB/polars) : ingestion, normalisation, fusions, mapping, contrôles
  → PostgreSQL/PostGIS
  → exports statiques : Parquet/JSON compact par élection + par territoire, PMTiles des contours
  → site statique SvelteKit + MapLibre GL JS + ECharts (calcul du score côté navigateur)
```
Bibliothèques : **MapLibre GL JS** (cartes vectorielles, open source, sans clé d'API) avec le protocole **PMTiles** (tuiles statiques servies depuis le CDN) ; **Apache ECharts** pour les diagrammes (courbes temporelles, barres empilées, radars, diagrammes de Sankey pour les reports de voix, accessibilité et export image inclus). D3 n'est utilisé que ponctuellement (échelles de couleur, cartogrammes) via `d3-scale`/`d3-scale-chromatic`.

Pas de serveur applicatif au MVP. Hébergement : CDN statique. L'état (élection, territoire, classement ajusté) est encodé dans l'URL. Laravel pourra être ajouté plus tard si des comptes ou un back-office deviennent nécessaires.

Découpage en unités :
- `etl/` : un module par source (parser → format commun), `territoires`, `mapping`, `validation`, `export`.
- `web/` : `map/`, `territory-panel/`, `ranking-editor/`, `score/` (fonction pure : résultats × classement → score, testable), `url-state/`.
- `docs/` : méthodologie, sources.

## 8. Fonctionnalités
MVP : carte choroplèthe par élection (score ou famille dominante) avec sélecteur de territoire, curseur temporel, fiche territoire (courbe de score, parts par famille, participation), comparaison de deux scrutins (glissement), éditeur de classement, partage par URL, page Sources et Méthodologie.
Ensuite : détection des bascules de famille dominante, communes les plus mobiles, estimation des reports de voix, export CSV, régionales/européennes, bureaux de vote des grandes villes.

## 9. Gestion des erreurs et qualité des données
- L'ETL échoue (et n'exporte pas) si : somme des voix ≠ exprimés, un code commune ne se résout pas, une liste n'a pas de famille.
- Les totaux nationaux/départementaux recalculés sont comparés aux totaux officiels ; tout écart au-delà d'un seuil documenté est signalé.
- Les lacunes connues (années sans détail communal, erreurs signalées par le CDSP) sont listées dans la page « Sources ».
- Côté web : un territoire sans donnée affiche un état vide explicite, jamais zéro.

## 10. Tests
- ETL : tests unitaires sur chaque parser avec échantillons réels réduits ; tests de non-régression sur des fusions de communes (cas types) ; contrôle des totaux sur 3-4 scrutins témoins.
- Fonction `score` : tests unitaires (cas limites : famille absente, classement personnalisé, abstention).
- Web : tests de composants, tests de bout en bout sur 5 territoires témoins (grande ville, sous-préfecture, commune fusionnée, département, pays).

## 11. Phasage
0. Référentiel territoires, communes cibles, contours, table de fusions.
1. Présidentielles + législatives 2002-2024 (commune), carte, fiche, score, éditeur de classement.
2. Municipales (2001-2026), départementales/cantonales ; régionales/européennes.
3. Séries historiques CDSP (1958-2002) avec marquage de précision ; glissements, bascules.
4. Fonctionnalités avancées (reports de voix, export, bureaux de vote).

## 12. Points à trancher avant le plan d'implémentation
- Validation du classement par défaut des familles (§6) : à relire avant publication.
- Existence de résultats municipaux communaux avant 2001 dans la banque CDSP (à tester en phase 0).
- Choix du CDN (SvelteKit confirmé).
