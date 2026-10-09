# Veille automatique (GitHub Actions, sans API payante)

Workflow : `.github/workflows/veille-quotidienne.yml` (tous les jours à 7 h, heure de Paris ; lancement manuel possible,
avec une case « simulation » qui ne publie rien). Aucun secret à configurer.

## Ce qui est réellement automatisé
1. Collecte des annonces de vente BureauxLocaux (8 départements × commerces, entrepôts, bureaux).
2. Contrôle des liens de toutes les annonces existantes (signalement seulement, rien n'est supprimé).
3. Ajout par règles (`scripts/ajouter_candidats.py`) des candidates qui présentent un intérêt pour un ERP de type L :
   usage de salle **décrit** par l'annonce (salle de réception, salle des fêtes, lieu de culte, salle de spectacle, amphithéâtre,
   salle polyvalente, restaurant avec couverts), puis usage seulement **évoqué** comme possibilité, ou type L écrit. Il faut
   prix, surface ≥ 150 m², commune, agence et lien, sans doublon. 10 ajouts maximum par jour, les usages décrits d'abord.
4. Resynchronisation de `index.html`, validation (`valider.py`), test des filtres (`test_filtres.js`).
5. Commit direct sur `main` (donc déploiement Netlify) **seulement** si des annonces ont été ajoutées et si tout a réussi.

## Statuts ERP (règle importante)
| Valeur `erp` | Étiquette du site | Attribué automatiquement quand… |
|---|---|---|
| `verifier` | **ERP à vérifier** | par défaut : le type L n'est pas confirmé (même si l'annonce parle d'ERP sans préciser le type) |
| `L` | **Type L confirmé** | une phrase de l'annonce écrit explicitement « type L » sans réserve ; elle est citée mot pour mot dans `erpSource` |
| `ERP` | ERP déclaré | jamais en automatique (statut réservé aux annonces existantes ou à une décision humaine) |

Une possibilité, un projet, une condition, un doute (« possibilité de type L », « transformable », « à confirmer », « N/L »,
« types M ou L »…) ne donne jamais « L ». Le filtre « Statut ERP » du site permet de retrouver chaque catégorie ; chaque fiche
affiche son étiquette. `valider.py` refuse un « L » sans citation du type L et toute modification du statut d'une annonce existante
(sauf `--autoriser`). Les statuts des annonces existantes ne sont jamais modifiés.

## Ce qui ne l'est pas (limites)
- Transports : toujours vides. Adresse : seulement si l'annonce donne une voie.
- 5 annonces déjà publiées sont classées « Type L confirmé » sans `erpSource` (eragny-reception, montereau-restaurant-reception-400,
  rambouillet-reception-950, versailles-reception-1000, vincennes-consultim). Leur statut est conservé ; `valider.py` les signale en alerte.
- Les annonces aux données ambiguës (doublon possible, vente ou location, VEFA, bureaux, prix incohérent, donnée manquante…) ne sont
  pas publiées ; elles sont listées dans `veille/diagnostic.json` (artefact du workflow, 14 jours) pour une relecture éventuelle.
- Une seule source est collectée automatiquement : BureauxLocaux. PAP, SeLoger, Leboncoin, Logic-Immo sont protégés contre les
  robots (aucun contournement) ; Geolocaux, ParuVendu, Cession PME, Bien'ici ne sont pas collectés par script.
- Les annonces ajoutées n'ont pas été relues par un humain : à vérifier avant toute démarche.
- Les liens retirés ne font l'objet d'aucune décision automatique.
