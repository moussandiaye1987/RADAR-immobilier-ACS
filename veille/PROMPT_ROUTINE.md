# Texte de la Routine quotidienne

À coller tel quel dans le champ « Instructions » de la Routine (claude.ai → Code → Routines).
Réglages : dépôt `moussandiaye1987/RADAR-immobilier-ACS`, environnement « Default » (réseau personnalisé
avec les domaines immobiliers), tous les jours à 6 h 55 (Europe/Paris), connecteur GitHub activé.

---

Tu exécutes la veille immobilière quotidienne du site « Radar ERP Type L » (dépôt GitHub moussandiaye1987/RADAR-immobilier-ACS, publié sur Netlify depuis main). Travaille en français. Tu es seul : ne pose pas de question, signale les doutes dans le bilan.

PHASE DE TEST : tu prépares une Pull Request et tu ne fusionnes JAMAIS rien. Ne pousse jamais sur main.

1. Dépôt
- `git fetch origin`. Si `veille/CONSIGNES.md` existe sur origin/main, la base est `main`. Sinon (outillage pas encore fusionné), la base est `claude/intelligent-tesla-11l0n8`.
- Crée la branche `veille/AAAA-MM-JJ` (date de Paris) depuis origin/<base>. Si la poussée de ce nom de branche est refusée, utilise la branche de travail attribuée à ta session.

2. Lis intégralement `veille/CONSIGNES.md` et `veille/sources.json`, puis applique-les à la lettre. Points non négociables :
- 8 départements : 75, 77, 78, 91, 92, 93, 94, 95.
- Aucune annonce existante supprimée ni passée en « vendu » ; les liens morts, redirigés ou non vérifiables sont seulement signalés, avec une décision proposée.
- Chaque nouvelle annonce est ouverte et vérifiée (prix, surface, commune, ERP, date, lien) et dédoublonnée ; rien d'inventé.
- `erp: "L"` seulement avec un justificatif écrit dans `erpSource`.
- Ne contourne aucune protection anti-robots (PAP, SeLoger, Leboncoin, Logic-Immo).
- Le code de index.html ne change pas : seule la copie des données est resynchronisée avec `python3 scripts/sync_index.py`.

3. Contrôles (tous doivent réussir) :
`python3 scripts/valider.py --base origin/main` puis `NODE_PATH=$(npm root -g) node scripts/test_filtres.js`.

4. Écris le bilan `veille/bilans/AAAA-MM-JJ.md` selon le modèle des consignes, fais le commit et pousse la branche, puis ouvre une Pull Request vers <base>, intitulée « Veille du JJ/MM/AAAA », dont la description reprend intégralement le bilan. S'il existe déjà une PR ouverte pour cette date, mets-la à jour. Si un contrôle échoue et que tu ne peux pas le corriger, ouvre la PR en brouillon avec l'erreur en tête du bilan. Si aucun outil ne te permet d'ouvrir la PR, pousse la branche et indique le lien de comparaison GitHub.

5. Termine par un message final court : lien de la PR, nombre d'annonces avant → après, nouvelles annonces, annonces actualisées, liens indisponibles ou non vérifiables, doublons évités, erreurs, et décisions attendues du propriétaire.
