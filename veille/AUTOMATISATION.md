# Veille du Radar ERP — Île-de-France : une seule veille quotidienne

**Depuis le 13/11/2026, une seule veille tourne** (demande du propriétaire : éviter plusieurs agents en parallèle) :

| Veille | État | Rôle |
|---|---|---|
| Routine Claude « Veille quotidienne Radar ERP (tous types) — site Netlify » (6 h 55, Paris) | **active** | recherche sur une vingtaine de sources, tous types d'ERP, publie elle-même sur `main` (PR du jour fusionnée si les contrôles passent) → Netlify. Texte : `veille/PROMPT_ROUTINE.md` |
| Workflow GitHub Actions `veille-quotidienne.yml` (BureauxLocaux, règles Python) | planification **arrêtée**, lancement manuel possible | décrit ci-dessous, conservé pour mémoire |
| Routine « Veille ERP tous types IDF (Radar ERP) » (tableau de bord artefact) | **désactivée** (réactivable) | alimentait un tableau de bord séparé, pas le site Netlify |

Pour réactiver le workflow GitHub Actions : remettre le bloc `schedule` indiqué en commentaire en tête du fichier.

---

## Historique : workflow GitHub Actions (lancement manuel uniquement)


Workflow : `.github/workflows/veille-quotidienne.yml` (tous les jours, déclenché à 05:00 UTC, soit 6 h à Paris en hiver
et 7 h en été ; lancement manuel possible, avec une case « simulation » qui ne publie rien). Aucun secret à configurer.

GitHub retarde souvent les tâches planifiées de plusieurs heures. Le workflow n'a donc **plus de garde horaire** : la
garde « 7 h à Paris » ajoutée en octobre ignorait toutes les exécutions retardées, et aucune veille n'a tourné du
22/10 au 09/11/2026 alors que les exécutions apparaissaient « réussies ».

## Ce qui est réellement automatisé
1. Collecte des annonces de vente BureauxLocaux (8 départements × commerces, entrepôts, bureaux), triées par
   pertinence pour un lieu de culte (`scripts/type_v.py`).
2. Contrôle des liens de toutes les annonces existantes (signalement seulement, rien n'est supprimé).
3. Ajout par règles (`scripts/ajouter_candidats.py`) des candidates utiles à un lieu de culte, dans cet ordre :
   lieu de culte ou bâtiment religieux **décrit** par l'annonce, salle des fêtes / polyvalente / associative, salle
   recevant du public, type V ou L écrit ; puis usage seulement **évoqué** (« idéal lieu de culte »…) ou destination
   d'intérêt collectif. Il faut prix, surface ≥ 150 m², commune, agence et lien, sans doublon. 10 ajouts maximum par jour.
4. Resynchronisation de `index.html`, tests des règles, validation (`valider.py`), test du site (`test_filtres.js`).
5. Commit direct sur `main` (donc déploiement Netlify) **seulement** si des annonces ont été ajoutées et si tout a réussi.
   Aucune validation manuelle n'est nécessaire.

## Statuts ERP (règle importante)
| Valeur `erp` | Étiquette du site | Attribué automatiquement quand… |
|---|---|---|
| `verifier` | **Potentiel Type V — à vérifier** | par défaut, **y compris pour un lieu de culte décrit** : le type V n'est pas écrit |
| `V` | **Type V confirmé** | une phrase de l'annonce écrit explicitement « type V » sans réserve ; elle est citée mot pour mot dans `erpSource` |
| `L` | **Salle Type L existante** | l'annonce écrit « type L », ou décrit une salle existante (réception, fêtes, spectacle, conférence) ; citation dans `erpSource` |

Une possibilité, un projet, une condition, un doute (« possibilité de type V », « transformable », « à confirmer »,
« L/V », « types L ou V »…) ne donne jamais « V ». Un restaurant (type N), une discothèque (type P), une salle
« ancienne » ou « désaffectée » ne donnent pas « L ». `valider.py` refuse un `V` sans citation du type V, un `L` sans
citation, et toute modification du statut ou archivage d'une annonce existante sans décision enregistrée.

## Profil du bien (`profil`)
`culte` (lieu de culte ou bâtiment religieux) · `associatif` (salle des fêtes, polyvalente, associative) ·
`salle` (salle recevant du public) · `transformable` (local à transformer). Les noms propres (Savigny-le-Temple,
rue du Temple, métro Église de Pantin, La Chapelle…) ne sont pas pris pour des lieux de culte.

## Passage du radar Type L au Type V (09/11/2026)
- Sauvegarde de la version Type L : branche `sauvegarde/radar-type-l-2026-11-09` (commit `2c59ae6`, site, données, scripts et workflow d'origine).
- `scripts/migrer_type_v.py` a relu le texte d'origine de chaque annonce encore en ligne (82 sur 131) et a reclassé
  les 131 annonces existantes (profil, statut, lecture type V). Aucune n'a été supprimée : 15 sont **archivées** (vendues
  occupées, plateaux en étage, annonce retirée), masquées par défaut et consultables avec leur motif. L'ancien statut est
  conservé dans `migration.erpAvant` et l'analyse d'origine dans `notes`. Chaque décision est justifiée dans
  `veille/migration_type_v.json`.

## Ce qui ne l'est pas (limites)
- Transports : toujours vides. Adresse : seulement si l'annonce donne une voie.
- Une seule source est collectée automatiquement : BureauxLocaux. Les ventes publiques et notariales, très utiles pour
  les chapelles et salles des fêtes (Agorastore, cessions de l'État, Immonot, Licitor, Interenchères), ne sont pas
  collectées par script. PAP, SeLoger, Leboncoin, Logic-Immo sont protégés contre les robots (aucun contournement).
- Les annonces aux données ambiguës (doublon possible, vente ou location, VEFA, bureaux, prix incohérent, donnée
  manquante…) ne sont pas publiées ; elles sont listées dans `veille/diagnostic.json` (artefact du workflow, 14 jours).
- Les annonces ajoutées n'ont pas été relues par un humain : à vérifier avant toute démarche (PLU, capacité, voisinage).
- Les liens retirés ne font l'objet d'aucune décision automatique.
