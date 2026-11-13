# Consignes de la veille quotidienne — Radar ERP — Île-de-France (tous types d'ERP)

> Depuis le 12/11/2026, le site couvre **tous les types d'ERP** (L, V, Y, M, N, O, P, R, S, T, U, W, X, J) avec un filtre « Type d'ERP ».
> Les règles du type V ci-dessous (statut `erp`, `profil`, `analyseV`) restent appliquées ; chaque annonce porte en plus
> `typesDeclares`, `typesPotentiels` et, si elle est citée, `categorie` (voir le tableau du §4).

Ces consignes sont suivies à chaque exécution de la Routine Claude Code (tous les jours à 6 h 55, heure de Paris).
Elles priment sur toute autre habitude. En cas de doute, **signaler dans le bilan plutôt que décider**.

**Veille unique (depuis le 13/11/2026)** : cette Routine est la SEULE veille quotidienne du radar. Le workflow GitHub
Actions `.github/workflows/veille-quotidienne.yml` n'est plus planifié (lancement manuel seulement) et l'ancienne
Routine « tableau de bord artefact » est désactivée. Voir `veille/AUTOMATISATION.md`.

## 0. Publication automatique (sans validation manuelle)

- Travailler sur une branche `veille/AAAA-MM-JJ` créée depuis `origin/main` à jour.
- Commit, poussée, puis **Pull Request vers `main`** intitulée « Veille du JJ/MM/AAAA ».
- **Si les contrôles du § 6 réussissent, fusionner soi-même la PR** (fusion « squash ») : `main` est publié sur
  Render automatiquement (https://radar-immobilier-acs.onrender.com). Si la fusion est refusée (conflit, protection), laisser la PR ouverte et le signaler.
- Si un contrôle échoue et ne peut pas être corrigé : PR en **brouillon**, non fusionnée, erreur en tête du bilan.
- Si rien n'a changé dans `annonces.json`, ne pas ouvrir de PR : le bilan est donné dans le message final.
- Ne jamais réutiliser ni fusionner une ancienne PR « Veille du … » : seule celle du jour compte.

## 1. Ce que l'on cherche

Locaux **à vendre** en Île-de-France pouvant accueillir un **lieu de culte (ERP de type V)**, par ordre de priorité :

1. **Lieux de culte existants ou anciens bâtiments religieux** : église, chapelle, temple, mosquée, synagogue,
   salle de prière, couvent, presbytère, local d'association cultuelle ;
2. **Salles des fêtes, salles polyvalentes, locaux ou salles associatives** ;
3. **Salles recevant du public** (réception, spectacle, conférence, séminaire, ancien cinéma ou théâtre) : une salle
   de type L existante se convertit en type V plus facilement qu'un local brut ;
4. **Locaux à transformer** présentant un vrai potentiel : grand volume de plain-pied, rez-de-chaussée, hauteur,
   bâtiment indépendant, parking, destination d'urbanisme « équipement d'intérêt collectif » (CINASPIC).

- Départements : 75, 77, 78, 91, 92, 93, 94, 95 (aucun autre).
- Filtres par défaut du site : budget 300 000 € – 2 000 000 €, surface ≥ 250 m². Ces filtres sont **réglables**
  par l'utilisateur : garder aussi les annonces pertinentes **hors de ces bornes** (jusqu'à ~6 M€, dès ~150 m²).
- Écarter : locations seules, cessions de fonds sans les murs, logements, terrains nus, biens hors Île-de-France,
  plateaux de bureaux en étage, biens vendus occupés (bail en cours).

Mots-clés de recherche : « lieu de culte à vendre », « ancienne église », « chapelle à vendre », « salle de prière »,
« salle des fêtes à vendre », « salle polyvalente », « local associatif », « équipement d'intérêt collectif », « ERP type V ».

## 2. Sources (voir `veille/sources.json`)

1. **BureauxLocaux** (source principale) : lancer `python3 scripts/collecter_bureauxlocaux.py`.
   Il parcourt les 8 départements × 3 types (commerces, entrepôts, bureaux) et écrit `veille/.candidats.json`.
2. **Geolocaux** (par département) et **ParuVendu** (Île-de-France) : lecture des pages de recherche
   avec `curl --compressed` ou le navigateur ; ne retenir que les annonces absentes du radar.
3. **Cession PME**, **Bien'ici** : navigateur Playwright uniquement, en complément.
4. **Ventes publiques et notariales** (Agorastore, cessions immobilières de l'État, Immonot, Licitor, Interenchères) :
   sources de premier ordre pour les chapelles, églises désacralisées et salles des fêtes vendues par les communes.
   **Bloquées dans l'environnement actuel** (voir `veille/sources.json`) : les consulter dès qu'elles sont autorisées.
5. **PAP, SeLoger, Leboncoin, Logic-Immo** : protégés contre les robots. **Ne pas tenter de contourner**
   ces protections. Les annonces existantes de ces sites sont conservées et signalées « non vérifiables ».

## 3. Sélection et vérification des nouvelles annonces

Dans `veille/.candidats.json`, examiner les candidates `connue: false` et `examinee: false`, **par score
décroissant** (le score de `scripts/type_v.py` place les lieux de culte décrits en tête), au maximum **30 fiches
par exécution** (le reste sera vu les jours suivants).

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
| `_id` | `commune-detail-surface` en minuscules sans accents, unique (ex. `vitry-ancien-lieu-de-culte-1103`) |
| `titre` | titre court et factuel, en français |
| `ville`, `adresse`, `dept`, `agence`, `ref`, `url` | tels que publiés ; `adresse` vide si non publiée |
| `prix` | entier en euros, `null` si « prix sur demande » |
| `surface` | entier en m² |
| `erp` | `V` (« Type V confirmé ») **uniquement** si l'annonce ou un document écrit explicitement « type V » sans réserve ; `L` (« Salle Type L existante ») si l'annonce écrit « type L » ou décrit une salle existante (réception, fêtes, spectacle, conférence) ; sinon `verifier` (« Potentiel Type V — à vérifier »), **y compris pour un lieu de culte décrit** |
| `profil` | `culte` (lieu de culte ou bâtiment religieux), `associatif` (salle des fêtes, polyvalente, associative), `salle` (salle recevant du public), `transformable` (local à transformer) |
| `erpDetail` | ce que dit l'annonce : catégorie, capacité, type, PMR, hauteur sous plafond… |
| `erpSource` | **obligatoire si `erp` = `V` ou `L`** : citation exacte de l'annonce ou du document, et son lien |
| `analyseV` | 1 à 3 phrases : profil, ce que dit l'annonce (citation), atouts, ce qui reste à vérifier pour un ERP V |
| `typesDeclares` | codes ERP cités explicitement par l'annonce (« ERP type M », « types M et L ») ou activité recevant du public en exploitation (restaurant → N, salle de réception → L, crèche → R, hôtel → O) ; un `erp` V ou L justifié vaut type déclaré |
| `typesPotentiels` | codes auxquels le local se prête sans être déclaré (grand volume de plain-pied → V, L, X ; vitrine → M ; bureaux → W ; cuisine/salle → N, L…), jamais un type déjà déclaré. `scripts/types_erp.py` les calcule |
| `categorie` | 1 à 5 si l'annonce cite la catégorie ERP |
| `parking` | `sur_place`, `proximite` ou `non_precise` |
| `transports` | liste de `{mode, ligne, station, distance, confirme}` ; `mode` parmi Métro, RER, Tram, Transilien, Bus ; `distance` en mètres ou `null` ; `confirme: true` seulement si l'annonce le dit |
| `statut` | `en_vente` (ou `sous_offre` si l'annonce l'indique) |
| `occupe` | `true` si vendu occupé / bail en cours |
| `notes` | 2 à 4 phrases : intérêt pour un lieu de culte, points de vigilance (PLU, copropriété, voisinage, stationnement, accessibilité, sanitaires et ablutions), prix au m² |
| `nouveau` | `true` |
| `ajoute` | horodatage en millisecondes de l'exécution |
| `vu` | date du jour `AAAA-MM-JJ` |

**Jamais** d'information inventée : ce qui n'est pas dans l'annonce reste vide, `null` ou « à vérifier ».
Ne jamais présenter un bien comme **conforme ou classé Type V sans justificatif** écrit (`erpSource`).
`scripts/type_v.py` applique ces règles ; `scripts/valider.py` refuse un `V` ou un `L` sans citation.

Après ajout, mettre `"date"` du fichier à la date du jour (`JJ/MM/AAAA`). L'étiquette `nouveau` des annonces
ajoutées lors des veilles précédentes est **retirée** quand elles ont plus de 7 jours (`vu` ancien).

## 5. Annonces existantes

- **Ne jamais supprimer** une annonce, ni la passer en `vendu` ou l'archiver (ce qui la masque du site), ni changer
  son statut ERP, sans décision explicite du propriétaire du radar.
- Une annonce **archivée** (`archive` = {date, motif}) reste dans `annonces.json` : le site la masque par défaut et
  l'affiche avec la case « Afficher les annonces archivées ». Les archives du passage au type V (09/11/2026) sont
  justifiées une à une dans `veille/migration_type_v.json`.
- Lancer `python3 scripts/verifier_liens.py` : il met à jour `veille/etat_liens.json` (statut de chaque lien,
  date du premier échec consécutif) sans toucher à `annonces.json`.
- Pour chaque lien `retiree`, `retiree_probable` ou `redirigee` : chercher si le bien est republié
  (`doublon_possible` dans les candidates). Le signaler dans le bilan avec une **proposition** de décision
  (garder, mettre à jour le lien, passer en `vendu`) — sans l'appliquer.
- Mises à jour autorisées sans validation : correction d'un prix ou d'une surface **vérifiés sur la page
  de l'annonce** (à détailler dans le bilan, ancienne → nouvelle valeur), passage en `sous_offre` si l'annonce
  l'affiche.

## 6. Contrôles obligatoires avant la fusion

```bash
python3 scripts/sync_index.py                          # recopie annonces.json dans index.html
python3 scripts/test_ajouter_candidats.py              # tests des règles
python3 scripts/valider.py --base origin/main          # JSON, champs, doublons, suppressions, types V et L
NODE_PATH=$(npm root -g) node scripts/test_filtres.js  # page et filtres dans Chromium
```

Les trois doivent réussir. Ne jamais modifier le code de `index.html` (seule la copie des données change).
En cas d'échec impossible à corriger : PR en **brouillon**, non fusionnée, avec l'erreur dans le bilan.

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
| _id | Commune (dept) | Surface | Prix | Profil | ERP | Lien | Pourquoi elle est retenue pour un lieu de culte |

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
