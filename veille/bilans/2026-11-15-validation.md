# Veille du 15/11/2026 — collecte de validation

> Exécution de validation lancée par le propriétaire dans la nuit du 15/11/2026 (branche `veille/2026-11-15-validation`). C'est la première exécution avec les sources Foncia, Laforêt, FNAIM et EOL. La veille planifiée de 6 h 55 utilisera `veille/2026-11-15`.

## Tableau par source

| Source | Pages lues | Annonces examinées | Retenues | Hors IDF | < 150 m² | Logement | Location seule | Fonds seul | Prix ou données manquants | Autre | Doublons déjà sur le radar | Doublons entre sources du jour | Accès |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BureauxLocaux | 24 pages de recherche (8 dép. × 3 types, script) + 6 fiches | 5 054 lues par le script ; 6 fiches examinées à la main | 3 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 1 (Montévrain = EOL) | ok |
| ParuVendu | 2 fiches issues de la recherche web | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 (annonces retirées, HTTP 410) | 0 | 0 | 0 | ok (pages de liste non relues aujourd'hui) |
| Foncia | 10 pages (`/achat/ile-de-france/local-commercial` et `/immeuble`, pages 1 à 5) ; 22 fiches ouvertes | 52 (24 locaux, 28 immeubles) | 6 | 0 | 17 | 28 | 0 | 0 | 0 | 1 | 0 | 0 | ok (HTTP 200 ; pages 3 à 5 vides : les 52 annonces sont sur les pages 1 et 2) |
| Laforêt | 16 pages (`achat-local-commercial-{dép.}` et `achat-bureau-{dép.}`) ; 25 fiches ouvertes | 124 | 16 | 0 | 100 | 2 | 0 | 0 | 1 | 3 | 1 (doublon possible) | 1 | ok ; `achat-bureau-yvelines` et `achat-bureau-hauts-de-seine` redirigent (301) vers la page région : 0 annonce pour ces deux départements |
| FNAIM | 5 pages (liste Île-de-France, pagination du site) ; 62 fiches ouvertes | 116 | 25 | 0 | 70 | 0 | 0 | 4 | 6 | 4 | 4 (dont 2 doublons possibles) | 3 | ok |
| EOL | 15 pages (formulaire vente, commerce + bureaux + entrepôt, ≥ 150 m², `start` 0 à 350) ; 12 fiches ouvertes | 123 distinctes (102 dans les 8 dép.) | 6 | 21 | 0 | 0 | 89 | 0 | 1 | 1 | 5 | 0 | ok, mais résultats peu fiables : beaucoup d'offres « à louer » malgré le filtre vente, et les pages au-delà de `start=175` répètent le même contenu |
| Recherche web / autres | 6 requêtes (O, P, T, J, Y + S, 92 + L) | 8 pistes | 0 | — | — | — | — | — | 2 | 4 (hors IDF, ventes déjà conclues, lieux à louer) | 2 (Paris 14e salle de danse, Nanterre) | 0 | ok |
| **Total** | | | **56** | | | | | | | | | | |

Les colonnes « écartées » d'une source font la somme suivante : examinées = retenues + écartées + doublons. Pour BureauxLocaux, la collecte automatique a lu 5 054 annonces (3 572 dans les critères larges, 252 déjà sur le radar, 95 déjà examinées) ; il reste 3 225 candidates à examiner, dont 1 686 prioritaires.

## Résumé
- Annonces sur le radar : avant 376 → après 432 (417 actives, 15 archivées)
- Nouvelles annonces : 56 · Annonces actualisées : 0 · Doublons évités : 17 (dont 4 « doublons possibles ») · Écartées : voir le tableau par source
- Liens : voir la section « Annonces indisponibles » (contrôle `verifier_liens.py`)
- Candidates BureauxLocaux restant à examiner : 3 225 (dont prioritaires 1 686)
- Contrôles : `test_ajouter_candidats.py` OK (28 tests) · `valider.py --base origin/main` OK (376 → 432, 56 nouvelles) · `test_filtres.js` OK (0 erreur JavaScript)

### Répartition des nouveautés par type d'ERP
| Type | Déclaré (cité par l'annonce ou activité en exploitation) | Potentiel |
|---|---|---|
| L — salles | 2 : Paris 19e (« VOLUME ERP 4 TYPE L »), Provins (salle de réception décrite) | 43 |
| M — commerces | 4 : pharmacie (Pierrefitte), boulangeries (Coupvray, Fontainebleau), boutique de sport (Paris 11e) | 29 |
| N — restaurants | 1 : Paris 9e, rue Richer (restaurant loué) | 18 |
| R — enseignement, formation | 1 : Paris 20e, organisme de formation (ERP 4e et 5e catégorie, salle de 300 personnes) | 0 |
| U — soins | 1 : Pierrefitte, centre dentaire | 0 |
| X — sport couvert | 1 : Saint-Maur-des-Fossés, salle de sport louée | 32 |
| W — bureaux | 0 | 28 |
| O, P, T, Y, S, J, V | 0 | 0 |
| Catégorie citée | 4e : Paris 20e (ensemble de formation), Paris 19e (volume type L) | |

Une seule annonce est en « Salle Type L existante » (`erp: L`) : Provins. Les 55 autres sont en « ERP à vérifier ». Paris 19e écrit « ERP 4 TYPE L » en capitales : `valider.py` ne reconnaît pas cette écriture pour un `erp: L`. L'annonce reste donc en « à vérifier », avec le type L déclaré et la citation dans `erpSource` (décision 2).

### Répartition par nature de la vente
| Nature | Nombre |
|---|---|
| Vente des murs | 41 |
| Murs vendus occupés (bail en cours) | 10 : Pierrefitte ×2, Coupvray, Paris 20e bureaux, Paris 20e ensemble de formation (à confirmer), Paris 4e, Saint-Maur, Paris 11e, Paris 9e, Fontainebleau |
| Murs et fonds | 2 : Voisenon (vendu avec mobilier et licence IV), Le Chesnay |
| Vente ou location à confirmer | 3 : Vaires-sur-Marne, Antony (EOL), Morainvilliers |

Répartition par département : 77 → 21 · 75 → 11 · 93 → 10 · 94 → 4 · 91 → 3 · 78 → 3 · 92 → 2 · 95 → 2.

## Nouvelles annonces
| _id | Commune (dept) | Surface | Prix | Déclarés / potentiels · cat. · nature | Lien | Titre |
|---|---|---|---|---|---|---|
| antony-local-mixte-atelier-hsp5-206 | Antony (92) | 206 m² | 785 000 € | – / L M W X · vente | [Foncia](https://fr.foncia.com/achat/antony-92160/local-commercial/00878822.htm) | Local mixte commercial de 206 m² avec atelier sous 5 m et terrasse (Antony) |
| paris20-gambetta-local-commercial-2-niveaux-223 | Paris 20e (75) | 223 m² | 1 370 000 € | – / L M N W · vente | [Foncia](https://fr.foncia.com/achat/paris-75020/local-commercial/00772207.htm) | Local commercial de 223 m² sur 2 niveaux avec pièce de 100 m² (Paris 20e, Gambetta) |
| pantin-immeuble-commercial-independant-verriere-504 | Pantin (93) | 504 m² | 3 800 000 € | – / L M N W X · vente | [Foncia](https://fr.foncia.com/achat/pantin-93500/local-commercial/00780954.htm) | Immeuble commercial indépendant de 504 m², majoritairement de plain-pied, verrière de 7 m (Pantin) |
| pierrefitte-gare-murs-centre-dentaire-occupe-171 | Pierrefitte-sur-Seine (93) | 171 m² | 355 000 € | **U** / M · murs occupés | [Foncia](https://fr.foncia.com/achat/pierrefitte-sur-seine-93380/local-commercial/00875474.htm) | Murs d'un centre dentaire de 171 m² vendus occupés, face à la gare RER (Pierrefitte-sur-Seine) |
| pierrefitte-gare-murs-pharmacie-occupee-173 | Pierrefitte-sur-Seine (93) | 173 m² | 355 000 € | **M** / – · murs occupés | [Foncia](https://fr.foncia.com/achat/pierrefitte-sur-seine-93380/local-commercial/00875475.htm) | Murs d'une pharmacie de 173 m² vendus occupés, face à la gare RER (Pierrefitte-sur-Seine) |
| coupvray-murs-boulangerie-occupee-160 | Coupvray (77) | 160 m² | 279 000 € | **M** / L X · murs occupés | [Foncia](https://fr.foncia.com/achat/coupvray-77700/local-commercial/00792611.htm) | Murs d'une boulangerie de 160 m² vendus occupés (Coupvray) |
| gagny-gare-bureau-pied-immeuble-vitrine-155 | Gagny (93) | 155 m² | 399 000 € | – / L M N W · vente | [Laforêt](https://www.laforet.com/agence-immobiliere/gagny/acheter/gagny/local-commercial-20069640) | Bureau de 155 m² en pied d'immeuble avec vitrine, près de la gare (Gagny) |
| pontault-combault-local-angle-vitrine-plain-pied-190 | Pontault-Combault (77) | 190 m² | 585 200 € | – / L M N X · vente | [Laforêt](https://www.laforet.com/agence-immobiliere/serris-val-deurope/acheter/pontault-combault/bureau-22409900) | Local de plain-pied de 190 m² en angle avec vitrine linéaire (Pontault-Combault) |
| maisons-alfort-grand-local-cour-salle-480 | Maisons-Alfort (94) | 480 m² | 1 050 000 € | – / L M N W X · vente | [Laforêt](https://www.laforet.com/agence-immobiliere/maisonsalfort/acheter/maisons-alfort/local-commercial-52236564) | Grand local commercial de 480 m² avec cour de 208 m² et salle de 75 m² (Maisons-Alfort) |
| corbeil-essonnes-murs-libres-ancien-bar-tabac-360 | Corbeil-Essonnes (91) | 360 m² | 370 000 € | – / L N W · vente | [Laforêt](https://www.laforet.com/agence-immobiliere/athismons/acheter/corbeil-essonnes/local-commercial-52290026) | Murs libres d'un ancien bar-tabac, immeuble mixte de 360 m² (Corbeil-Essonnes) |
| saint-ouen-l-aumone-bureaux-accueil-10-places-207 | Saint-Ouen-l'Aumône (95) | 207 m² | 270 000 € | – / L W · vente | [Laforêt](https://www.laforet.com/agence-immobiliere/saint-ouen-laumone/acheter/saint-ouen-l-aumone/bureau-52304589) | Bureaux de 207 m² avec espace d'accueil et 10 places de parking (Saint-Ouen-l'Aumône) |
| ris-orangis-bureaux-open-space-6-places-210 | Ris-Orangis (91) | 210 m² | 224 500 € | – / L W · vente | [Laforêt](https://www.laforet.com/agence-immobiliere/risorangis/acheter/ris-orangis/bureau-52578617) | Bureaux de 210 m² avec open space et 6 places de parking, près du tram T12 (Ris-Orangis) |
| argenteuil-centre-entrepot-pc-surelevation-500 | Argenteuil (95) | 500 m² | 569 000 € | – / L W X · vente | [Laforêt](https://www.laforet.com/agence-immobiliere/argenteuil/acheter/argenteuil/local-commercial-52647169) | Entrepôt de 500 m² en centre-ville sur parcelle de 765 m², permis de surélévation (Argenteuil) |
| bagnolet-entrepot-libre-a3-400 | Bagnolet (93) | 400 m² | 530 000 € | – / L X · vente | [Laforêt](https://www.laforet.com/agence-immobiliere/aulnaysousbois/acheter/bagnolet/local-commercial-52772312) | Entrepôt de 400 m² libre de toute activité, près de l'A3 (Bagnolet) |
| moissy-cramayel-ferme-arvigny-local-activite-187 | Moissy-Cramayel (77) | 187 m² | 182 000 € | – / L N W X · vente | [Laforêt](https://www.laforet.com/agence-immobiliere/moissycramayel-lieusaint/acheter/moissy-cramayel/local-commercial-52858120) | Local d'activité de 187 m² avec atelier et mezzanine, Ferme d'Arvigny (Moissy-Cramayel) |
| paris20-maraichers-bureaux-loues-464 | Paris 20e (75) | 464 m² | 2 520 000 € | – / L W · murs occupés | [Laforêt](https://www.laforet.com/agence-immobiliere/paris20gambetta/acheter/paris-20/bureau-52887014) | Bureaux de 464 m² vendus loués, divisibles en 2 lots (Paris 20e, Maraîchers) |
| paris10-faubourg-saint-martin-local-verriere-428 | Paris 10e (75) | 428 m² | 3 180 000 € | – / L N · vente | [Laforêt](https://www.laforet.com/agence-immobiliere/paris10saintdenis/acheter/paris-10/local-commercial-52961241) | Local de 428 m² sur 2 niveaux sous verrière, sur cour arborée (Paris 10e, Louis Blanc) |
| paris20-alexandre-dumas-ensemble-formation-erp4-1179 | Paris 20e (75) | 1179 m² | 6 500 000 € | **R** / L M W X · cat. 4 · murs occupés | [Laforêt](https://www.laforet.com/agence-immobiliere/paris20avron/acheter/paris-20/local-commercial-52974876) | Ensemble de 1 179 m² exploité par un organisme de formation, ERP 4e et 5e catégorie, salle de 300 personnes (Paris 20e) |
| chanteloup-en-brie-activite-hsp10-bureaux-600 | Chanteloup-en-Brie (77) | 600 m² | 1 115 000 € | – / L N W X · vente | [Laforêt](https://www.laforet.com/agence-immobiliere/serris-val-deurope/acheter/chanteloup-en-brie/local-commercial-52983890) | Local d'activité de 600 m² sous 10 m de hauteur avec 150 m² de bureaux (Chanteloup-en-Brie) |
| paris04-ile-saint-louis-murs-occupes-180 | Paris 4e (75) | 180 m² | 1 300 000 € | – / M · murs occupés | [Laforêt](https://www.laforet.com/agence-immobiliere/paris15vaugirard/acheter/paris-04/local-commercial-52989217) | Murs commerciaux de 180 m² vendus occupés, Île Saint-Louis (Paris 4e) |
| saint-maur-pont-de-creteil-murs-salle-sport-louee-530 | Saint-Maur-des-Fossés (94) | 530 m² | 670 000 € | **X** / L M · murs occupés | [Laforêt](https://www.laforet.com/agence-immobiliere/saint-maur-adamville/acheter/saint-maur-des-fosses/local-commercial-53018273) | Murs d'une salle de sport indépendante de 530 m² vendus loués (Saint-Maur-des-Fossés) |
| montreuil-local-professionnel-hall-accueil-157 | Montreuil (93) | 157 m² | 754 000 € | – / L N W X · vente | [Laforêt](https://www.laforet.com/agence-immobiliere/noisy-le-grand-immobilier-entreprise/acheter/montreuil/bureau-53002567) | Local professionnel de 157 m² avec hall d'accueil (Montreuil) |
| vaires-sur-marne-local-neuf-pmr-359 | Vaires-sur-Marne (77) | 359 m² | 646 200 € | – / L M X · vente ou location | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/45127343/17-acheter-localcommercial-vaires-sur-marne-77360.htm) | Local commercial neuf de 359 m² sur site clos, accès PMR (Vaires-sur-Marne) |
| paris11-charonne-murs-boutique-sport-occupee-341 | Paris 11e (75) | 341 m² | 1 980 000 € | **M** / L W X · murs occupés | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/45731323/17-acheter-localcommercial-paris-75.htm) | Murs d'une boutique d'articles de sport de 341 m² vendus occupés (Paris 11e, boulevard de Charonne) |
| chelles-chantereine-batiment-independant-showroom-480 | Chelles (77) | 480 m² | 800 000 € | – / L M W X · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/46432005/17-acheter-localcommercial-chantereine-77500.htm) | Bâtiment indépendant rénové de 480 m² avec showroom et cour (Chelles, Chantereine) |
| fontainebleau-rue-grande-local-salle-202-281 | Fontainebleau (77) | 281 m² | 449 000 € | – / L M W X · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/46856421/17-acheter-localcommercial-fontainebleau-77300.htm) | Local commercial de 281 m² avec salle principale de 202 m², rue Grande (Fontainebleau) |
| la-ferte-gaucher-batiment-commercial-artisanal-libre-1000 | La Ferté-Gaucher (77) | 1000 m² | 240 000 € | – / M · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/50714184/17-acheter-localcommercial-la-ferte-gaucher-77320.htm) | Bâtiment commercial et artisanal d'environ 1 000 m² vendu libre, sur 2 000 m² de terrain (La Ferté-Gaucher) |
| voisenon-immeuble-restaurant-licence-iv-236 | Voisenon (77) | 236 m² | 399 000 € | – / L N · murs et fonds | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/51316466/17-acheter-localcommercial-voisenon-77950.htm) | Immeuble de 236 m² avec salle de restaurant, vendu avec mobilier et licence IV (Voisenon) |
| paris09-richer-murs-restaurant-occupe-184 | Paris 9e (75) | 184 m² | 985 000 € | **N** / L M · murs occupés | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/51890491/17-acheter-localcommercial-paris-75.htm) | Murs d'un restaurant de 184 m² vendus occupés, rue Richer (Paris 9e) |
| melun-centre-ville-emplacement-commercial-150 | Melun (77) | 150 m² | 130 000 € | – / M · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/52429764/17-acheter-localcommercial-melun-77000.htm) | Emplacement commercial d'environ 150 m² à l'entrée du quartier piéton (Melun) |
| serris-parc-international-food-court-terrasse-431 | Serris (77) | 431 m² | 1 310 565 € | – / L N W X · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/52574389/17-acheter-localcommercial-serris-77700.htm) | Local neuf de 431 m² dédié à la restauration (« food court ») avec terrasse de 132 m² (Serris) |
| serris-parc-international-showroom-rdc-possibilite-erp-223 | Serris (77) | 223 m² | 573 864 € | – / M · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/52848204/17-acheter-localcommercial-serris-77700.htm) | Cellule de 223 m² en RDC à usage de showroom, « possibilité ERP » (Serris) |
| rambouillet-atelier-bureaux-terrain-2200-343 | Rambouillet (78) | 343 m² | 250 000 € | – / L W X · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/52608696/17-acheter-localcommercial-rambouillet-78120.htm) | Atelier-bureaux-entrepôt de 343 m² sur terrain de 2 200 m² (Rambouillet) |
| montreuil-carnot-murs-local-double-acces-156 | Montreuil (93) | 156 m² | 480 000 € | – / L M N W X · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/52741491/17-acheter-localcommercial-montreuil-93100.htm) | Murs d'un local commercial de 156 m² avec double accès sur rue, place Carnot (Montreuil) |
| mouroux-magasin-700-terrain-750 | Mouroux (77) | 750 m² | 450 000 € | – / M · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/52817885/17-acheter-localcommercial-mouroux-77120.htm) | Local commercial de 750 m² (magasin d'environ 700 m²) vendu libre, sur l'axe D934 (Mouroux) |
| paris20-cbre-commerce-neuf-657 | Paris 20e (75) | 657 m² | 1 700 000 € | – / L M X · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/52823704/17-acheter-localcommercial-paris-75.htm) | Commerce neuf de 657 m² non divisible (Paris 20e) |
| paris19-ourcq-volume-erp4-type-l-248 | Paris 19e (75) | 248 m² | 1 200 000 € | **L** / X · cat. 4 · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/52936772/17-acheter-localcommercial-paris-19-75019.htm) | Murs d'un volume « ERP 4 type L » de 258 m² SUBL, HSP 4,25 m (Paris 19e, rue de l'Ourcq) |
| draveil-local-neuf-vefa-vitrine-12m-170 | Draveil (91) | 170 m² | 337 050 € | – / L M N X · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/53051851/17-acheter-localcommercial-draveil-91210.htm) | Local commercial neuf de 169 m² en VEFA avec vitrine de 12 m (Draveil) |
| paris16-passy-restaurant-bar-et-appartement-210 | Paris 16e (75) | 210 m² | 2 300 000 € | – / L M N · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/53077443/17-acheter-localcommercial-paris-75016.htm) | Local de restauration-bar de 128 m² + sous-sol et appartement de 82 m², libres (Paris 16e, Passy) |
| provins-local-restaurant-salle-reception-339 | Provins (77) | 339 m² | 267 500 € | **L** / M N · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/53099104/17-acheter-localcommercial-provins-77160.htm) | Local commercial de 339 m² avec salle de restaurant et salle de réception (Provins) |
| paris16-local-mixte-jardin-extraction-pmr-170 | Paris 16e (75) | 170 m² | 2 040 000 € | – / L M N · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/53183122/17-acheter-localcommercial-paris-75016.htm) | Local commercial mixte de 170 m² avec jardin de 70 m², extraction et accès PMR (Paris 16e) |
| noisy-le-sec-cbre-surface-commerciale-brut-1422 | Noisy-le-Sec (93) | 1422 m² | 3 270 600 € | – / M · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/53200732/17-acheter-localcommercial-seine-saint-denis-93.htm) | Surface commerciale neuve de 1 422 m² divisible dès 148 m², livrée brute en septembre 2027 (Noisy-le-Sec) |
| fontainebleau-murs-boulangerie-occupee-325 | Fontainebleau (77) | 325 m² | 644 800 € | **M** / – · murs occupés | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/53202384/17-acheter-localcommercial-fontainebleau-77300.htm) | Murs d'une boulangerie de 325 m² vendus occupés, entre gare et centre (Fontainebleau) |
| ivry-moulin-local-baie-vitree-sous-sol-livraisons-300 | Ivry-sur-Seine (94) | 300 m² | 530 000 € | – / M · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/53221142/17-acheter-localcommercial-val-de-marne-94.htm) | Local commercial de 300 m² avec baie vitrée filante, RDC + sous-sol accessible aux camions (Ivry-sur-Seine) |
| montreuil-ancienne-tannerie-atelier-plain-pied-310 | Montreuil (93) | 310 m² | 990 000 € | – / L X · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/53229722/17-acheter-localcommercial-montreuil-93100.htm) | Atelier de plain-pied de 310 m², ancienne tannerie sur cour, permis mixte (Montreuil) |
| le-chesnay-murs-et-fonds-2-niveaux-363 | Le Chesnay (78) | 363 m² | 1 785 000 € | – / M · murs et fonds | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/46845226/17-acheter-localcommercial-le-chesnay-78150.htm) | Local de 363 m² sur 2 niveaux vendu murs et fonds, proche mairie (Le Chesnay) |
| chelles-coudreaux-deux-locaux-terrain-1000-436 | Chelles (77) | 436 m² | 549 000 € | – / L M W X · vente | [FNAIM](https://www.fnaim.fr/annonce-immobiliere/53154732/17-acheter-localcommercial-seine-et-marne-77.htm) | Deux locaux commerciaux de 436 m² à rénover sur terrain de plus de 1 000 m² (Chelles, Coudreaux) |
| romainville-entrepot-bureaux-plain-pied-351 | Romainville (93) | 351 m² | 1 100 000 € | – / L W X · vente | [EOL](https://www.eol.fr/annonce-144555.html) | Entrepôt avec bureaux de 351 m², accès de plain-pied et hall d'accueil (Romainville) |
| antony-batiment-independant-activites-bureaux-328 | Antony (92) | 328 m² | 850 000 € | – / L N W X · vente ou location | [EOL](https://www.eol.fr/annonce-54798.html) | Bâtiment indépendant d'activités et bureaux de 328 m² avec salle de conférence (Antony) |
| collegien-local-activite-bureaux-hsp6-471 | Collégien (77) | 471 m² | 775 000 € | – / L W X · vente | [EOL](https://www.eol.fr/annonce-49011.html) | Local d'activité avec bureaux de 471 m², hauteur jusqu'à 6,50 m, 7 places (Collégien) |
| montevrain-innovespace-activite-hsp8-580 | Montévrain (77) | 580 m² | 990 000 € | – / L W X · vente | [EOL](https://www.eol.fr/annonce-82673.html) | Local d'activité neuf de 580 m² sous 8 m avec bureaux, 10 places (Montévrain, Innovespace) |
| la-queue-en-brie-batiment-independant-entrepot-1086 | La Queue-en-Brie (94) | 1086 m² | 1 300 000 € | – / L X · vente | [EOL](https://www.eol.fr/annonce-144259.html) | Bâtiment indépendant à usage d'entrepôt de 1 086 m² sous 6 m (La Queue-en-Brie) |
| morainvilliers-zac-orme-activite-bureaux-282 | Morainvilliers (78) | 282 m² | 340 000 € | – / L W X · vente ou location | [EOL](https://www.eol.fr/annonce-151055.html) | Local d'activités et bureaux de 282 m² avec mezzanine, ZAC de l'Orme (Morainvilliers) |
| claye-souilly-batiment-commercial-independant-plain-pied-380 | Claye-Souilly (77) | 380 m² | 880 000 € | – / L M X · vente | [BL](https://www.bureauxlocaux.com/annonce/batiment-commercial-a-vendre--40636841) | Bâtiment commercial indépendant de 380 m² de plain-pied avec parking, zone commerciale (Claye-Souilly) |
| saint-thibault-des-vignes-local-activite-hsp5-586 | Saint-Thibault-des-Vignes (77) | 586 m² | 680 000 € | – / L W X · vente | [BL](https://www.bureauxlocaux.com/annonce/local-dactivites-de-586m2--42855834) | Local d'activité de 586 m² avec 332 m² de bureaux, hauteur 5 m (Saint-Thibault-des-Vignes) |
| meaux-zi-nord-batiment-independant-activite-2167 | Meaux (77) | 2167 m² | 1 700 000 € | – / L W X · vente | [BL](https://www.bureauxlocaux.com/annonce/local-dactivite-a-vendre--39236544) | Bâtiment indépendant d'activités de 2 167 m² sur 3 697 m² de terrain clos (Meaux, ZI Nord) |
Points d'attention (détaillés dans `notes`) :
- **Murs occupés** (10 annonces) : ce sont des investissements, sans usage possible avant la fin du bail. Pour Paris 20e (ensemble de formation de 1 179 m²), l'annonce dit seulement que le bien est « actuellement exploité par un organisme de formation » : bail ou libération à confirmer. Le prix (6,5 M€) dépasse le plafond habituel du radar ; l'annonce est gardée parce qu'elle décrit un ERP déjà classé avec une salle de 300 personnes.
- **Biens non livrés** : Noisy-le-Sec (CBRE, livraison en septembre 2027) et Draveil (VEFA, livraison au 4e trimestre 2026).
- **Partie habitation** : Corbeil-Essonnes, Voisenon, Paris 16e Passy, Fontainebleau (boulangerie) et La Queue-en-Brie comprennent un logement. La surface recevant du public est plus petite que la surface totale.
- **Destination limitée par l'annonce** : Serris 223 m² (showroom, professions libérales, BtoB), Serris 431 m² (restauration), Maisons-Alfort (« activité non bruyante et non polluante »), Montreuil Carnot (pas de restauration).
- **Données à confirmer** : Paris 20e CBRE (« commerce neuf » ou « entrepôt »), Melun (150 m² pour 130 000 € : murs ou droit au bail ?), La Ferté-Gaucher (« environ 1 000 m² »), Morainvilliers (558 m² sur la liste EOL, 282 m² sur la fiche).
- **Pierrefitte-sur-Seine** : deux lots voisins (centre dentaire, pharmacie), même agence, même prix ; deux fiches distinctes.

## Annonces actualisées
| _id | Champ | Avant | Après | Vérifié sur |
|---|---|---|---|---|
| — | — | — | — | Aucune modification d'annonce existante |

## Annonces indisponibles ou à vérifier (aucune modification appliquée)
`scripts/verifier_liens.py` a contrôlé les 432 liens : ok 338 · retirées 11 · retirées probables 60 · redirigées 17 · non vérifiables 6 · erreurs 0. Les 40 « erreurs » du 14/11 (fnaim.fr, geolocaux.com…) répondent désormais : fnaim.fr est joignable.

| _id | Statut du lien | Depuis | Republiée ? | Décision proposée |
|---|---|---|---|---|
| chilly-mazarin-vigne-aux-loups-981, les-loges-en-josas-batiment-1200, meaux-zi-nord-loue-815, montlhery-local-independant-1621, saint-ouen-l-aumone-vert-galant-1500, taverny-verdun-la-plaine-1090 | retiree (HTTP 410, SeLoger Bureaux & Commerces) | 13/11 (vu le 15/11) | non trouvée | Nouveau : le site répond « 410 » (annonce supprimée) malgré sa protection. Proposer « vendu » après vérification manuelle |
| crecy-la-chapelle-domaine-reception-3106, saint-fargeau-ponthierry-domaine-reception-1500 | retiree (HTTP 404, espaces-atypiques.com) | 13/11 | non trouvée | Vérifier sur le site de l'agence, puis proposer « vendu » |
| noisy-le-sec-cbre-2540, saint-aubin-route-de-l-orme-1096 | retiree (HTTP 410) | 13/11 | non trouvée | Proposer « vendu » après vérification manuelle (déjà signalé le 14/11) |
| kremlin-bicetre-303 (archivée) | retiree (HTTP 410) | 08/10 | possible : BL n° 43017342 | Comparer ; mettre à jour le lien si même bien |
| le-plessis-pate-local-independant-869 | ok (lesiteimmo) | — | même bien sur EOL n° 92250, à 1 300 000 € HT (radar : 1 350 000 €) | Garder ; écart de prix à vérifier (prix non modifié) |
| sarcelles-eol-1232, serris-cbre-962-ght, saint-fargeau-ponthierry-mare-aux-loups-1749, paris03-beaumarchais-erp5-363 et 12 autres | redirigee | 13/11–14/11 | même annonce (URL modifiée) | Garder ; mettre à jour l'URL si vous le souhaitez (liste complète dans `veille/etat_liens.json`) |
| mandres-les-roses-perdrix-1093 | redirigee vers l'accueil BureauxLocaux | 13/11 | non trouvée | Probablement retirée : proposer « vendu » |
| 60 annonces « retirées probables » | page de recherche BureauxLocaux | 10/2026 – 11/2026 | voir `veille/etat_liens.json` | Garder ; revérifier (liste identique au 14/11) |

## Annonces non vérifiables
6 annonces de sites protégés (PAP, SeLoger Bureaux & Commerces) : voir `veille/etat_liens.json` (statut `non_verifiable`).

## Doublons évités
| Annonce trouvée | Correspond à | Raison |
|---|---|---|
| FNAIM 53160406 (Coulommiers, 1 930 m², 988 000 €) | coulommiers-showrooms-erp-1930 | Même ensemble de showrooms (prix à ±1,2 %) |
| FNAIM 53162640 (Serris, 361 m², 1 096 533 €, Karéa) | serris-parc-international-locaux-commerciaux-361 | Même lot du Parc international (prix à +3,0 %) |
| EOL 8136, 52915, 54898, 495 (Montreuil Mozinor 1 080 m², Torcy 917 m², Villepinte 800 m², Sarcelles 1 232 m²) | montreuil-mozinor-1080, torcy-evolis-900, villepinte-erables-800, sarcelles-eol-1232 | Même commune, surface et prix |
| EOL 92250 (Le Plessis-Pâté, 869 m², 1 300 000 €) | le-plessis-pate-local-independant-869 (1 350 000 €) | Même bâtiment ; écart de prix de 3,8 % signalé ci-dessus |
| BL 42855865 (Montévrain, 580 m², 1 000 000 €, Scamac) | montevrain-innovespace-activite-hsp8-580 (EOL, 990 000 €) | Même bien (Innovespace, 450 + 130 m², 10 places) chez deux sources ; fiche créée depuis EOL |
| Laforêt 53027829 (Les Lilas, 300 m²) | Laforêt 52397710 (écartée : logement) | Même annonce sous deux références d'agence |
| FNAIM 51680717 (Montreuil, garage Peugeot) | FNAIM 51680610 (écartée) | Même lot, deux références |
| FNAIM 53218894 (Noisy-le-Sec, 635 m²) | noisy-le-sec-cbre-surface-commerciale-brut-1422 | Même opération CBRE (lots divisibles dès 148 m²) |
| Paris 14e, salle de danse 285 m² (BL 40828824, recherche web) ; Nanterre 1 692 m² (BL 43183910) | déjà sur le radar / déjà examinée | Même URL |
| **Doublon possible** — Laforêt 52939337 (Buc, 1 232 m², 1 400 000 €) | buc-fourny-1203 (Arthur Loyd, 1 203 m², prix non publié) | Même rue probable, surface à +2,4 % : non ajoutée |
| **Doublon possible** — FNAIM 52870879 (Arcueil, 419 m², 1 133 000 €, Agence Joffard) | arcueil-n20 (Evolis, 419 m², 959 179 €) | Même surface, prix différent de 18 % : non ajoutée |
| **Doublon possible** — FNAIM 53242854 (Paris 18e, 293 m², 1 495 000 €, Perenium, métro Guy Môquet) | paris17-guy-moquet-300 (300 m², 1 400 000 €) | Même secteur, surface à −2,3 %, prix à +6,8 % : non ajoutée |
| **Doublon possible** — FNAIM 52807163 (Pontault-Combault, 184 m², 582 000 €, Étude Gindra) | pontault-combault-local-angle-vitrine-plain-pied-190 (Laforêt, 190 m², 585 200 €) | Prix à 0,5 %, surface à 3,2 % : une seule fiche créée |

## Annonces écartées (principales)
| Lien | Motif |
|---|---|
| Foncia : 28 immeubles (Bourg-la-Reine 710 m², Noisy-le-Grand et Champs-sur-Marne 4 M€, Montreuil, Houilles…) | Immeubles de rapport d'habitation (logement) |
| [Foncia Les Ulis 200 m²](https://fr.foncia.com/achat/les-ulis-91940/local-commercial/00878011.htm) | Plateau de bureaux au 1er étage, en partie loué |
| [Foncia Paris 19e atelier d'artiste](https://fr.foncia.com/achat/paris-75019/local-commercial/00768586.htm) | 132 m² Carrez (151 m² au sol), sous le seuil |
| [Laforêt Les Lilas 300 m²](https://www.laforet.com/agence-immobiliere/leslilas/acheter/les-lilas/local-commercial-52397710) ; [Noisy-le-Grand 200 m²](https://www.laforet.com/agence-immobiliere/noisy-le-grand-immobilier-entreprise/acheter/noisy-le-grand/bureau-52621863) | Boutique avec deux étages d'habitation ; maison bourgeoise (logement) |
| [Laforêt Fontenay-aux-Roses](https://www.laforet.com/agence-immobiliere/bourglareine/acheter/fontenay-aux-roses/local-commercial-21586891) | 4 boutiques occupées de 52 à 104 m² (lots < 150 m²) |
| Laforêt Issy-les-Moulineaux 201 m², Morsang-sur-Orge 267 m² | Locaux au 1er étage (plateaux en étage) |
| [Laforêt Châtenay-Malabry](https://www.laforet.com/agence-immobiliere/bourglareine/acheter/chatenay-malabry/local-commercial-52605959) | 739 m² = surface de la parcelle ; surface bâtie non publiée |
| [Laforêt Paris 10e rue Paradis](https://www.laforet.com/agence-immobiliere/paris10saintmartin/acheter/paris-10/local-commercial-52962421) | 97 m² Carrez en RDC + 45 m² en sous-sol (< 150 m²) |
| FNAIM Villiers-sur-Marne, Saint-Maur (miroiterie), Fontainebleau (restaurant, boutique) | Fonds de commerce ou droit au bail seul |
| [FNAIM Courbevoie 1 078 m²](https://www.fnaim.fr/annonce-immobiliere/52010391/17-acheter-localcommercial-courbevoie-92400.htm) | « Nous consulter pour le prix », locataire en place depuis 2013 |
| FNAIM Boulogne-Billancourt (murs libres), Breux-Jouy, Gif-sur-Yvette, Persan, Paris 13e boutique | Surface non publiée |
| FNAIM Montreuil (garage Peugeot + maison), Arpajon (garage automobile), Créteil (5 petits lots occupés) | Murs occupés sans accueil du public significatif ou lots < 150 m² |
| [FNAIM Paris 13e 220 m²](https://www.fnaim.fr/annonce-immobiliere/51929058/17-acheter-localcommercial-paris-13-75013.htm) | Ancien cabinet médical au 1er étage |
| EOL Alfortville 713 m² | Entrepôt logistique à quais (vente ou location) |
| EOL : 89 offres « à louer » et 21 hors Île-de-France | Location seule ; hors des 8 départements |
| [BL n° 40265513 Ivry-sur-Seine](https://www.bureauxlocaux.com/annonce/415-m2-rdc-avec-vitrine-entree-independante-ivry-s--40265513) | Données incohérentes (415 m² dans le titre, 1 903 m² dans les données, 413 000 €) : à revoir, l'annonce décrit un RDC « ERP able » |
| BL n° 40694034 Paris 17e (immeuble de 1 096 m²) | Location seule |
| ParuVendu 1287366906 (Franconville, hôtel et salle de réception 1 100 m²) et 1285842493 (Paris, hôtel) | Annonces retirées (HTTP 410) |

## Sources consultées et erreurs
- **Foncia** : les deux pages de liste de `sources.json` sont lisibles (HTTP 200, HTML rendu côté serveur). Les pages 3 à 5 répondent mais sont vides : 24 locaux commerciaux et 28 immeubles en Île-de-France. Aucune URL à paramètres utilisée. 22 fiches ouvertes.
- **Laforêt** : 16 pages départementales lues. `achat-bureau-yvelines` et `achat-bureau-hauts-de-seine` redirigent (301) vers `/region/achat-bureau-ile-de-france` : aucun bureau listé pour ces deux départements. `achat-local-commercial-yvelines`, absente de `sources.json`, existe (1 annonce). Pas de deuxième page (moins de 40 annonces par département). 25 fiches ouvertes.
- **FNAIM** : 5 pages lues (pagination fournie par le site) : 116 annonces, dont 62 sans surface ou ≥ 150 m², toutes ouvertes. Le prix est presque toujours présent sur la fiche.
- **EOL** : formulaire de recherche exact de `sources.json` (redirection vers `search_id=159898131`), 15 pages lues jusqu'à `start=350`. Les pages au-delà de `start=175` répètent le même contenu, et la liste mêle des offres « à louer » malgré le filtre vente. 102 annonces sont dans les 8 départements, mais seulement 13 sont à vendre. 12 fiches ouvertes.
- **BureauxLocaux** : collecte complète (5 054 annonces, 0 erreur). 6 fiches examinées par ordre de score ; la priorité du jour est allée aux quatre nouvelles sources.
- **ParuVendu, Geolocaux** : pages de liste non relues lors de cette exécution de validation, seulement 2 fiches ParuVendu (retirées).
- **Recherche web** : 6 requêtes (hôtels O, danse et discothèques P, galeries et expositions T, EHPAD et résidences seniors J, musées et bibliothèques Y/S, Hauts-de-Seine et salles de réception L). Aucune annonce nouvelle de type Y, S, T, J, O ou P en vente en Île-de-France. Avec les 24 recherches BureauxLocaux et les 30 pages de liste des quatre nouvelles sources, l'exigence de 15 requêtes variées est couverte.
- **Sources protégées** (PAP, SeLoger, SeLoger Bureaux & Commerces, Leboncoin, Logic-Immo) : non consultées ; aucun contournement.
- **Contrôles** : `test_ajouter_candidats.py` OK (28 tests) · `valider.py --base origin/main` OK (376 → 432, 56 nouvelles) · `test_filtres.js` OK (0 erreur JavaScript).

## Décisions attendues de votre part
1. Ajouts nombreux (56) : la première lecture des quatre nouvelles sources a fait remonter des biens jamais vus. Faut-il garder les entrepôts et locaux d'activité en zone industrielle (Meaux, Collégien, Montévrain, Saint-Thibault, La Queue-en-Brie, Chanteloup) ? Ou le radar doit-il se limiter aux biens en centre-ville ?
2. paris19-ourcq-volume-erp4-type-l-248 : l'annonce écrit « VOLUME ERP 4 TYPE L » en capitales. Faut-il passer l'annonce en « Salle Type L existante » ? Il faudrait pour cela que `valider.py` accepte « TYPE L » en majuscules.
3. paris20-alexandre-dumas-ensemble-formation-erp4-1179 : prix de 6,5 M€, au-dessus du plafond habituel. Faut-il la garder ?
4. Doublons possibles non ajoutés : Buc (Laforêt 52939337), Arcueil (FNAIM 52870879), Paris 18e (FNAIM 53242854), Pontault-Combault (FNAIM 52807163). Faut-il créer des fiches distinctes ?
5. Six annonces SeLoger Bureaux & Commerces répondent désormais « 410 » (chilly-mazarin-vigne-aux-loups-981, les-loges-en-josas-batiment-1200, meaux-zi-nord-loue-815, montlhery-local-independant-1621, saint-ouen-l-aumone-vert-galant-1500, taverny-verdun-la-plaine-1090). Les deux domaines de réception espaces-atypiques.com répondent « 404 ». Faut-il passer ces annonces en « vendu » ?
6. le-plessis-pate-local-independant-869 : EOL affiche 1 300 000 € HT contre 1 350 000 € sur le radar. Faut-il corriger le prix et ajouter le lien EOL ?
7. `veille/sources.json` : faut-il noter que les pages Laforêt `achat-bureau-yvelines` et `achat-bureau-hauts-de-seine` redirigent vers la région, que `achat-local-commercial-yvelines` existe, et que la pagination EOL est instable au-delà de `start=175` ?
8. Questions toujours ouvertes du 14/11 : noisy-le-sec-cbre-2540, saint-aubin-route-de-l-orme-1096 et mandres-les-roses-perdrix-1093 (« vendu » ?), kremlin-bicetre-303 (republication BL n° 43017342 ?).
