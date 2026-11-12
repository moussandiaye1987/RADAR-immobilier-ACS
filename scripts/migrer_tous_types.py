"""Ajoute typesDeclares / typesPotentiels / categorie aux annonces qui ne les ont pas encore.

Usage : python3 scripts/migrer_tous_types.py
Les fiches déjà classées (champ typesDeclares présent) ne sont pas modifiées. Idempotent.
"""
from commun import ecrire_annonces, lire_annonces
from types_erp import appliquer

if __name__ == "__main__":
    payload = lire_annonces()
    n = 0
    for r in payload["rows"]:
        if "typesDeclares" not in r:
            appliquer(r)
            n += 1
    ecrire_annonces(payload)
    print(f"{n} annonces classées par type d'ERP sur {len(payload['rows'])}")
