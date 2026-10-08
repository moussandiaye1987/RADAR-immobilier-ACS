"""Réécrit annonces.json au format du dépôt et recopie ses données dans index.html.

Usage : python3 scripts/sync_index.py
Seul le contenu de <script id="data"> change dans index.html ; le reste de la page est intact.
"""
from commun import ecrire_annonces, lire_annonces

if __name__ == "__main__":
    payload = lire_annonces()
    ecrire_annonces(payload)
    print(f"index.html synchronisé : {len(payload['rows'])} annonces, relevé du {payload['date']}")
