# Consignes de la veille quotidienne — Radar ERP Type V (lieux de culte)

Ces consignes sont suivies à chaque exécution de la Routine Claude Code (tous les jours à 6 h 55, heure de Paris).
Elles priment sur toute autre habitude. En cas de doute, **signaler dans le bilan plutôt que décider**.

## 0. Phase de test : règles de publication

- Travailler sur une branche `veille/AAAA-MM-JJ` créée depuis `main` à jour.
- Ouvrir une **Pull Request vers `main`** et **ne jamais la fusionner**. Ne jamais pousser sur `main`.
- Si une branche ou une PR du même jour existe déjà, la mettre à jour au lieu d'en créer une autre.
- Si rien n'a changé (aucune nouvelle annonce, aucun lien modifié), ouvrir quand même la PR avec le bilan
  (seuls `veille/etat_liens.json`, `veille/examinees.json` et le bilan changent).

## 1. Ce que l'on cherche

Locaux **à vendre** en Île-de-France susceptibles d'accueillir une **activité cultuelle (ERP de type V)**, par priorité :

1. **Lieux de culte existants** ou locaux destinés au culte (église, temple, mosquée, synagogue, salle de prière, association cultuelle) ;
2. **Anciens bâtiments religieux** ou anciens usages cultuels (chapelle désaffectée, ancienne église, presbytère, couvent) ;
3. **Locaux associatifs** et équipements d'intérêt collectif ;
4. **Salles recevant déjà du public** (réception, fêtes, polyvalentes, spectacle, conférence) ;
5. **Grands locaux à transformer** : plain-pied, grand volume, annoncés ERP ou ouverts au public.

- Départements : 75, 77, 78, 91, 92, 93, 94, 95 (aucun autre).
- Filtres par défaut du site : budget 300 000 € – 2 000 000 €, surface ≥ 250 m². Ces filtres sont **réglables** :
  garder aussi les annonces pertinentes **hors de ces bornes** (jusqu'à ~6 M€, dès ~150 m²).
- Écarter : locations seules, cessions de fonds sans les murs, logements, terrains nus, biens hors Île-de-France,
  plateaux de bureaux en étage, biens vendus occupés sans perspective de libération.

## 2. Sources (voir `veille/sources.json`)

1. **BureauxLocaux** (source principale) : lancer `python3 scripts/collecter_bureauxlocaux.py`.
   Il parcourt les 8 départements × 3 types (commerces, entrepôts, bureaux) et écrit `veille/.candidats.json`.
2. **Geolocaux** (par département) et **ParuVendu** (Île-de-France) : lecture des pages de recherche
   avec `curl --compressed` ou le navigateur ; ne retenir que les annonces absentes du radar.
3. **Cession PME**, **Bien'ici** : navigateur Playwright uniquement, en complément.
4. **PAP, SeLoger, Leboncoin, Logic-Immo** : protégés contre les robots. **Ne pas tenter de contourner**
   ces protections. Les annonces existantes de ces sites sont conservées et signalées « non vérifiables ».

## 3. Sélection et vérification des nouvelles annonces

Dans `veille/.candidats.json`, examiner les candidates `connue: false` et `examinee: false`, **par score
décroissant**, au maximum **30 fiches par exécution** (le reste sera vu les jours suivants).

Pour chaque candidate examinée :

1. **Ouvrir la page de l'annonce** et vérifier : en vente, prix, surface, commune, adresse, agence, référence,
   date de publication si indiquée, occupation (bail en cours), parking, transports cités.
2. **Doublons** : si `doublon_possible` n'est pas vide, comparer avec les annonces citées (même bien republié,
   autre agence, autre numéro). Même bien → ne pas créer de nouvelle annonce ; si l'annonce du radar a un
   lien mort, le signaler dans le bilan comme « republiée » avec le nouveau lien (sans remplacer l'URL sans
   validation). Deux agences différentes pour un bien similaire → garder les deux, et le noter.
3. **Décider** : retenue (ajout au radar) ou écartée (avec un motif court).
4. **Noter la décision** dans `veille/examinees.json` :
   `"<numéro>": {"date": "AAAA-MM-JJ", "decision": "retenue" | "ecartee" | "doublon", "motif": "…", "_id": "…"}`.

## 4. Format d'une annonce ajoutée (`annonces.json`)

Respecter exactement le format existant (voir une annonce récente) :

| Champ | Règle |
|---|---|
| `_id` | `commune-detail-surface` en minuscules sans accents, unique (ex. `sartrouville-reception-529`) |
| `titre` | titre court et factuel, en français |
| `ville`, `adresse`, `dept`, `agence`, `ref`, `url` | tels que publiés ; `adresse` vide si non publiée |
| `prix` | entier en euros, `null` si « prix sur demande » |
| `surface` | entier en m² |
| `erp` | classement ERP cité par l'annonce : `L` **uniquement avec un justificatif** ; `ERP` si l'annonce déclare un ERP sans préciser le type ; sinon `verifier` |
| `typeV` | `V` (**Type V confirmé**) **uniquement avec un justificatif écrit** dans `typeVSource` ; `L` (**Salle Type L existante**) seulement si `erp` = `L` ; sinon `potentiel` (**Potentiel Type V — à vérifier**) |
| `typeVSource` | **obligatoire si `typeV` = `V`** : citation exacte de l'annonce ou du procès-verbal qui mentionne le type V, et son lien |
| `profil` | `culte_existant`, `ancien_religieux`, `associatif`, `salle` ou `transformation` (voir § 1) |
| `erpDetail` | ce que dit l'annonce : catégorie, capacité, type, PMR, hauteur sous plafond… |
| `erpSource` | **obligatoire si `erp` = `L`** : citation exacte de l'annonce ou du document qui mentionne le type L, et son lien |
| `parking` | `sur_place`, `proximite` ou `non_precise` |
| `transports` | liste de `{mode, ligne, station, distance, confirme}` ; `mode` parmi Métro, RER, Tram, Transilien, Bus ; `distance` en mètres ou `null` ; `confirme: true` seulement si l'annonce le dit |
| `statut` | `en_vente` (ou `sous_offre` si l'annonce l'indique) |
| `occupe` | `true` si vendu occupé / bail en cours |
| `notes` | 2 à 4 phrases : intérêt pour un lieu de culte, points de vigilance (PLU et changement de destination, commission de sécurité, effectif, copropriété, stationnement, voisinage, accessibilité), prix au m² |
| `nouveau` | `true` |
| `ajoute` | horodatage en millisecondes de l'exécution |
| `vu` | date du jour `AAAA-MM-JJ` |

**Jamais** d'information inventée : ce qui n'est pas dans l'annonce reste vide, `null` ou « à vérifier ».
Ne jamais présenter un bien comme **Type V confirmé sans justificatif** écrit : un ancien lieu de culte, une salle
de prière ou un « idéal lieu de culte » restent « Potentiel Type V — à vérifier ».

Après ajout, mettre `"date"` du fichier à la date du jour (`JJ/MM/AAAA`). L'étiquette `nouveau` des annonces
ajoutées lors des veilles précédentes est **retirée** quand elles ont plus de 7 jours (`vu` ancien).

## 5. Annonces existantes

- **Ne jamais supprimer** une annonce, ni la passer en `vendu` ou l'archiver (`archive`), ni changer son `typeV`,
  sans décision explicite du propriétaire du radar. Proposer ces décisions dans le bilan.
- Lancer `python3 scripts/verifier_liens.py` : il met à jour `veille/etat_liens.json` (statut de chaque lien,
  date du premier échec consécutif) sans toucher à `annonces.json`.
- Pour chaque lien `retiree`, `retiree_probable` ou `redirigee` : chercher si le bien est republié
  (`doublon_possible` dans les candidates). Le signaler dans le bilan avec une **proposition** de décision
  (garder, mettre à jour le lien, passer en `vendu`) — sans l'appliquer.
- Mises à jour autorisées sans validation : correction d'un prix ou d'une surface **vérifiés sur la page
  de l'annonce** (à détailler dans le bilan, ancienne → nouvelle valeur), passage en `sous_offre` si l'annonce
  l'affiche.

## 6. Contrôles obligatoires avant la PR

```bash
python3 scripts/sync_index.py                          # recopie annonces.json dans index.html
python3 scripts/valider.py --base origin/main          # JSON, champs, doublons, suppressions, Type V / Type L, archives
NODE_PATH=$(npm root -g) node scripts/test_filtres.js  # page et filtres dans Chromium
```

Les trois doivent réussir. Ne jamais modifier le code de `index.html` (seule la copie des données change).
En cas d'échec impossible à corriger : ouvrir quand même la PR, en **brouillon**, avec l'erreur dans le bilan.

## 7. Bilan quotidien

Écrire `veille/bilans/AAAA-MM-JJ.md` et le reprendre **intégralement** dans la description de la PR :

```markdown
# Veille du JJ/MM/AAAA

## Résumé
- Annonces sur le radar : avant N → après N
- Nouvelles annonces : N · Annonces actualisées : N · Doublons évités : N · Écartées : N
- Liens : ok N · retirées N · retirées probables N · redirigées N · non vérifiables N · erreurs N
- Candidates restant à examiner : N (dont prioritaires N)

## Nouvelles annonces
| _id | Commune (dept) | Surface | Prix | Statut Type V | Profil | Lien | Pourquoi elle est retenue |

## Annonces actualisées
| _id | Champ | Avant | Après | Vérifié sur |

## Annonces indisponibles ou à vérifier (aucune modification appliquée)
| _id | Statut du lien | Depuis | Republiée ? | Décision proposée |

## Annonces non vérifiables
(sites protégés : liste des _id)

## Doublons évités
| Annonce trouvée | Correspond à | Raison |

## Annonces écartées (principales)
| Lien | Motif |

## Sources consultées et erreurs
- Source : pages lues, annonces lues, erreurs éventuelles
- Résultat des contrôles : valider.py, test_filtres.js

## Décisions attendues de votre part
(liste numérotée, une ligne par décision)
```
