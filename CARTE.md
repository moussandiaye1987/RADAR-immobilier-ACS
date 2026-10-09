# Carte interactive (Leaflet + OpenStreetMap)

Bouton **Liste / Carte** au-dessus des annonces. La carte est chargée à la première ouverture (la liste reste l'affichage par défaut).

- **Bibliothèques** : Leaflet 1.9.4 et Leaflet.markercluster 1.5.3, copiées dans `vendor/` (aucun CDN, licences incluses).
- **Fond de carte** : tuiles OpenStreetMap (gratuites, sans clé ; attribution affichée). Aucune API payante.
- **Position** : si une annonce porte `lat` et `lng` dans `annonces.json` (en Île-de-France), ce point est utilisé. Sinon, la carte place le repère au **centre approximatif de la commune** (`data/communes_idf.json`, 1 278 entrées), et la fiche l'indique : ce n'est jamais l'adresse du bien. Pour Paris, tous les arrondissements partent du centre de Paris. Une commune introuvable n'apparaît pas sur la carte ; le compteur sous la carte le signale.
- **Filtres** : la carte affiche exactement les annonces de la liste (tous les filtres existants s'appliquent).
- **Regroupement** : les repères proches sont regroupés en grappes ; un clic zoome, au zoom maximal les repères superposés s'écartent.
- **Données des communes** : `python3 scripts/generer_communes.py` (centres calculés à partir des contours IGN Admin Express, licence ouverte). À relancer seulement si des communes fusionnent.
- **Tests** : `python3 scripts/test_carte_donnees.py` et `NODE_PATH=$(npm root -g) node scripts/test_filtres.js` (bouton, repères, synchronisation avec les filtres, fiche, regroupement, coordonnées exactes, mobile).
