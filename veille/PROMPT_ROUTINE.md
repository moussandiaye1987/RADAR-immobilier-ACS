# Texte de la Routine quotidienne (veille unique du radar)

Texte en place dans la Routine « Veille quotidienne Radar ERP (tous types) — site Render » (claude.ai → Code → Routines),
tous les jours à 6 h 55 (Europe/Paris). C'est la seule veille quotidienne du radar depuis le 13/11/2026.

---

Tu exécutes la veille immobilière quotidienne du site « Radar ERP — Île-de-France » (dépôt GitHub moussandiaye1987/RADAR-immobilier-ACS, publié automatiquement sur Render (https://radar-immobilier-acs.onrender.com) depuis main). Le radar recense les locaux à VENDRE en Île-de-France pouvant recevoir du public, TOUS TYPES D'ERP confondus, classés par type. C'est la SEULE veille du radar : elle publie elle-même, sans validation manuelle. Travaille en français. Tu es seul : ne pose pas de question, signale les doutes dans le bilan.

Types d'ERP (codes) : L salles (spectacle, réunion, réception, polyvalente) ; V lieux de culte ; Y musées ; M magasins, commerces, showrooms ; N restaurants, débits de boissons ; O hôtels ; P danse, jeux ; R enseignement, crèches, formation ; S bibliothèques ; T expositions ; U soins ; W administrations, banques, bureaux ; X sport couvert ; J accueil personnes âgées / handicapées.

1. Dépôt
- Si le dépôt n'est pas déjà dans le répertoire de travail, ajoute-le (outil add_repo, owner moussandiaye1987, repo RADAR-immobilier-ACS, accès push) puis clone-le.
- `git fetch origin`. Base : `main`. Crée la branche `veille/AAAA-MM-JJ` (date de Paris) depuis origin/main. Si la poussée de ce nom de branche est refusée, utilise la branche de travail attribuée à ta session.
- N'utilise, ne mets à jour ni ne fusionne AUCUNE ancienne PR « Veille du … » : seule la PR du jour compte.

2. Lis intégralement `veille/CONSIGNES.md` et `veille/sources.json`, puis applique-les. Points non négociables :
- 8 départements : 75, 77, 78, 91, 92, 93, 94, 95. Annonces de VENTE uniquement.
- Recherche tous types d'ERP (au moins 15 requêtes variées couvrant plusieurs types et plusieurs sources).
- Aucune annonce existante supprimée, archivée, passée en « vendu » ni déclassée ; les liens morts, redirigés ou non vérifiables sont seulement signalés, avec une décision proposée.
- Chaque nouvelle annonce est ouverte et vérifiée (prix, surface, commune, ERP, date, lien) et dédoublonnée (même URL, ou même ville + surface + prix) ; rien d'inventé.
- typesDeclares seulement si l'annonce cite le type ou décrit l'activité en exploitation, avec la citation dans `erpSource` ; sinon typesPotentiels uniquement. Renseigne `categorie` si elle est citée, ainsi que `profil` et l'analyse avec scripts/types_erp.py et scripts/type_v.py.
- Ne contourne aucune protection anti-robots (PAP, SeLoger, Leboncoin, Logic-Immo).
- Classement non confirmé : `erp: "verifier"` et `typesDeclares: []` ; le site affiche alors « ERP à vérifier ». Ne modifie jamais le classement d'une annonce existante.
- Aucune API payante, aucun nouveau service : uniquement la recherche web, la lecture des pages et les scripts du dépôt.
- Publie UNIQUEMENT dans le dépôt GitHub (main). N'écris rien dans un Artifact et n'agis jamais directement chez l'hébergeur : Render redéploie seul le site à chaque commit sur main.
- Le code de index.html ne change pas : seule la copie des données est resynchronisée avec `python3 scripts/sync_index.py`.

3. Contrôles (tous doivent réussir) : `python3 scripts/test_ajouter_candidats.py`, `python3 scripts/valider.py --base origin/main` puis `NODE_PATH=$(npm root -g) node scripts/test_filtres.js`.

4. Publication
- Si annonces.json n'a pas changé : pas de PR ; passe à l'étape 5.
- Sinon : écris le bilan `veille/bilans/AAAA-MM-JJ.md` selon le modèle des consignes (avec la répartition des nouveautés par type d'ERP), commit, pousse la branche et ouvre une Pull Request vers main intitulée « Veille du JJ/MM/AAAA », dont la description reprend le bilan.
- Si les trois contrôles ont réussi, FUSIONNE toi-même cette PR (méthode squash) : c'est la publication voulue par le propriétaire, sans validation manuelle. Vérifie ensuite que main contient le commit. Si la fusion est refusée (conflit : refais la branche depuis origin/main à jour et recommence une fois ; sinon protection), laisse la PR ouverte et signale-le.
- Si un contrôle échoue et que tu ne peux pas le corriger : PR en brouillon, NON fusionnée, avec l'erreur en tête du bilan.

5. Termine par un message final court : publication faite ou non (lien de la PR), nombre d'annonces avant → après, nouvelles annonces par type d'ERP, annonces actualisées, liens indisponibles ou non vérifiables, doublons évités, erreurs, et décisions attendues du propriétaire.
