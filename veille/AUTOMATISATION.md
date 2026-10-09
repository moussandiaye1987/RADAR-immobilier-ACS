# Veille automatique (GitHub Actions, sans API payante)

Workflow : `.github/workflows/veille-quotidienne.yml` (tous les jours à 7 h, heure de Paris ; lancement manuel possible,
avec une case « simulation » qui ne publie rien). Aucun secret à configurer.

## Ce qui est réellement automatisé
1. Collecte des annonces de vente BureauxLocaux (8 départements × commerces, entrepôts, bureaux).
2. Contrôle des liens de toutes les annonces existantes (signalement seulement, rien n'est supprimé).
3. Ajout par règles (`scripts/ajouter_candidats.py`) des candidates dont l'annonce **décrit elle-même** un usage de salle
   (salle de réception, salle des fêtes, lieu de culte, salle de spectacle, amphithéâtre, salle polyvalente, restaurant avec
   nombre de couverts), avec prix, surface ≥ 150 m², commune, agence et lien, sans doublon. 10 ajouts maximum par jour.
4. Resynchronisation de `index.html`, validation (`valider.py`), test des filtres (`test_filtres.js`).
5. Commit direct sur `main` (donc déploiement Netlify) **seulement** si des annonces ont été ajoutées et si tout a réussi.

## Ce qui ne l'est pas (limites)
- `erp` vaut « ERP » si l'annonce déclare un classement, sinon « verifier ». **Jamais « L »** : aucun justificatif de type L
  ne peut être établi par règle. Transports : toujours vides. Adresse : seulement si l'annonce donne une voie.
- Les annonces ambiguës (usage « possible », doublon possible, vente ou location, VEFA, bureaux, prix incohérent…) ne sont
  pas publiées ; elles sont listées dans `veille/diagnostic.json` (artefact du workflow, 14 jours) pour une relecture éventuelle.
- Une seule source est collectée automatiquement : BureauxLocaux. PAP, SeLoger, Leboncoin, Logic-Immo sont protégés contre les
  robots (aucun contournement) ; Geolocaux, ParuVendu, Cession PME, Bien'ici ne sont pas collectés par script.
- Les annonces ajoutées n'ont pas été relues par un humain : à vérifier avant toute démarche.
- Les liens retirés ne font l'objet d'aucune décision automatique.
