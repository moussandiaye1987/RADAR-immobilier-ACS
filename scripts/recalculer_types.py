"""Corrige `typesPotentiels` (potentiel V injustifié retiré) et ajoute `nature` (nature de la vente). Idempotent.

Usage : python3 scripts/recalculer_types.py [--simulation]

Retire le potentiel « V » (lieu de culte) déduit pour presque tous les biens par l'ancienne règle (audit du
14/11/2026) ; les autres potentiels déjà notés sont conservés : un potentiel n'est qu'une piste d'usage, jamais une autorisation ERP. Ne modifie JAMAIS `erp`,
`typesDeclares`, `categorie`, `profil`, `archive` ni aucun autre champ : le script s'arrête si c'était le cas.
"""
import argparse
import collections
import json
import sys

from commun import ecrire_annonces, lire_annonces
from types_erp import nature_vente, types

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--simulation", action="store_true")
    a = p.parse_args()
    payload = lire_annonces()
    avant = collections.Counter(t for r in payload["rows"] for t in r.get("typesPotentiels", []))
    for r in payload["rows"]:
        fige = json.dumps({k: r.get(k) for k in ("erp", "typesDeclares", "categorie", "profil", "archive", "statut")}, sort_keys=True)
        _, pot, _ = types(r)
        garder_v = "V" in pot  # V justifié (mot cultuel dans la description du bien, profil culte ou associatif)
        r["typesPotentiels"] = [c for c in (r.get("typesPotentiels") or []) if c != "V" or garder_v]
        r["nature"] = nature_vente(r)
        if json.dumps({k: r.get(k) for k in ("erp", "typesDeclares", "categorie", "profil", "archive", "statut")}, sort_keys=True) != fige:
            sys.exit(f"ERREUR {r['_id']} : un champ de classement aurait changé : abandon")
    apres = collections.Counter(t for r in payload["rows"] for t in r["typesPotentiels"])
    print("potentiels avant :", dict(avant.most_common()))
    print("potentiels après :", dict(apres.most_common()))
    print("nature de la vente :", dict(collections.Counter(r["nature"] for r in payload["rows"])))
    if not a.simulation:
        ecrire_annonces(payload)
