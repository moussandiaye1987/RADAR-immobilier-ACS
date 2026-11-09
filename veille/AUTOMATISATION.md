# Veille automatique — Radar ERP Type V (lieux de culte)

Workflow : `.github/workflows/veille-quotidienne.yml`. Une exécution par jour, au premier déclencheur qui tombe à 7 h ou plus
tard (heure de Paris) ; lancement manuel possible, avec une case « simulation » qui ne publie rien. Aucun secret, aucune API payante.

## Ce qui est réellement automatisé
1. Collecte des annonces de vente BureauxLocaux (8 départements × commerces, entrepôts, bureaux). Le score de priorité
   favorise les indices cultuels (lieu de culte, église, temple, mosquée, synagogue, salle de prière, presbytère…).
2. Contrôle des liens de toutes les annonces existantes (signalement seulement, rien n'est supprimé).
3. Ajout par règles (`scripts/ajouter_candidats.py`) des candidates utiles à une activité cultuelle, par priorité de profil :
   | Profil (`profil`) | Étiquette du site | Exemples d'indices dans l'annonce |
   |---|---|---|
   | `culte_existant` | Lieu de culte existant | lieu de culte, salle de prière, église, temple, mosquée, synagogue, association cultuelle |
   | `ancien_religieux` | Ancien bâtiment religieux | ancienne église, chapelle désaffectée, presbytère, couvent, « anciennement occupé par une association évangélique » |
   | `associatif` | Local associatif | local associatif, équipement d'intérêt collectif, maison des associations |
   | `salle` | Salle recevant du public | salle de réception, des fêtes, polyvalente, de spectacle, de conférence |
   | `transformation` | Local à transformer | grand local (≥ 300 m²) commercial ou d'activités, de plain-pied, annoncé ERP ou ouvert au public (3 ajouts/jour maximum) |

   À profil égal, un usage **décrit** passe avant un usage seulement **évoqué** (« idéal lieu de culte »). Les noms de communes
   (Savigny-le-Temple), de rues (rue de l'Église), d'arrêts (Église de Pantin) et les repères (« face à l'église ») sont ignorés.
   Il faut prix, surface ≥ 150 m², commune, agence et lien, sans doublon. 10 ajouts maximum par jour.
4. Resynchronisation de `index.html`, validation (`valider.py`), test de la page, des filtres et de la carte (`test_filtres.js`).
5. Commit direct sur `main` (donc déploiement Netlify) **seulement** si des annonces ont été ajoutées et si tout a réussi.
   Aucune validation manuelle des annonces.

## Statuts Type V (règle importante)
| Valeur `typeV` | Étiquette du site | Attribué automatiquement quand… |
|---|---|---|
| `potentiel` | **Potentiel Type V — à vérifier** | par défaut : aucun justificatif du type V |
| `V` | **Type V confirmé** | une phrase de l'annonce écrit explicitement « type V » sans réserve ; elle est citée mot pour mot dans `typeVSource` |
| `L` | **Salle Type L existante** | une phrase de l'annonce écrit explicitement « type L » sans réserve (citée dans `erpSource`, `erp` = « L ») |

Une déduction (« ancienne église », « lieu de culte »), une possibilité, un projet, une condition ou un doute
(« type V probable », « possibilité de type V », « à confirmer », « L/V », « types L ou V ») ne donne **jamais** « V ».
`valider.py` refuse un « V » sans citation du type V, un « L » sans classement ERP « L », toute modification du statut
Type V d'une annonce existante et tout archivage non autorisé (sauf `--autoriser`). Le champ `erp` d'origine est conservé.

## Archivage (aucune suppression)
Une annonce hors périmètre porte `archive: true`, `archiveMotif` et `archiveDate`. Elle reste dans `annonces.json`,
est masquée par défaut et s'affiche avec l'option « Afficher les annonces archivées » (étiquette « Archivée », repère gris).
La veille automatique n'archive jamais rien : l'archivage est une décision humaine.

## Migration du 09/11/2026 (Type L → Type V)
`scripts/migrer_type_v.py` (idempotent) a réévalué les 131 annonces : 5 « Salle Type L existante » (ancien classement L),
126 « Potentiel Type V — à vérifier », aucune « Type V confirmé » (aucune annonce ne cite le type V) ; profils attribués après
relecture des fiches ; 12 annonces archivées (vendues occupées, plateaux de bureaux en étage, rez-de-chaussée trop petit).
Une analyse « Type V » (`analyseV`) est ajoutée à chaque fiche ; les notes d'origine sont conservées.
Sauvegarde de la version Type L : branche `sauvegarde/radar-type-l-2026-11-09`.

## Ce qui ne l'est pas (limites)
- Transports : toujours vides pour les ajouts automatiques. Adresse : seulement si l'annonce donne une voie.
- 5 annonces « Salle Type L existante » n'ont pas de citation `erpSource` (statut hérité du radar Type L) ; `valider.py` les signale.
- Les annonces aux données ambiguës (doublon possible, vente ou location, VEFA, bureaux, prix incohérent, donnée manquante…) ne sont
  pas publiées ; elles sont listées dans `veille/diagnostic.json` (artefact du workflow, 14 jours).
- Une seule source est collectée automatiquement : BureauxLocaux. PAP, SeLoger, Leboncoin, Logic-Immo sont protégés contre les
  robots (aucun contournement). Les ventes de collectivités (anciens presbytères, chapelles) se trouvent plutôt sur Agorastore ou
  les ventes notariales : liens sur le site, pas de collecte automatique.
- Les annonces ajoutées n'ont pas été relues par un humain : à vérifier (PLU, ERP, commission de sécurité) avant toute démarche.

## Historique de fonctionnement
- 09/10/2026 : test réel réussi sur GitHub Actions (collecte, contrôles, poussée vers la branche jetable `ci-test-publication`).
- 25/10 → 09/11/2026 : toutes les exécutions planifiées ont été ignorées (GitHub les déclenchait entre 10 h et 15 h UTC, hors de
  l'ancienne fenêtre 7 h 00–7 h 59). Corrigé le 09/11/2026 : garde « une fois par jour à partir de 7 h » avec marqueur en cache.
