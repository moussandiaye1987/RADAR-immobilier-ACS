"""Tests des données de la carte (data/communes_idf.json) et de la normalisation des noms de communes.

Usage : python3 scripts/test_carte_donnees.py
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import DEPTS, RACINE, lire_annonces  # noqa: E402
from generer_communes import norm_ville  # noqa: E402

COMMUNES = json.loads((RACINE / "data" / "communes_idf.json").read_text(encoding="utf-8"))


class DonneesCarte(unittest.TestCase):
    def test_fichier_communes(self):
        self.assertGreaterEqual(len(COMMUNES), 1270)       # 1 276 communes des 8 départements
        for cle, (lat, lng) in COMMUNES.items():
            self.assertIn(cle.split("|")[0], DEPTS, cle)
            self.assertTrue(47.9 < lat < 49.4 and 1.2 < lng < 3.8, f"{cle} hors Île-de-France : {lat}, {lng}")

    def test_normalisation(self):
        self.assertEqual(norm_ville("Saint-Maur-des-Fossés"), norm_ville("St Maur des Fosses"))
        self.assertEqual(norm_ville("Créteil"), norm_ville("Creteil"))
        self.assertEqual(norm_ville("Les Mureaux"), norm_ville("Mureaux"))
        self.assertEqual(norm_ville("Garges-lès-Gonesse"), "gargeslesgonesse")
        self.assertEqual(norm_ville("Paris"), "paris")

    def test_toutes_les_annonces_ont_une_position(self):
        """Les villes actuelles du radar se placent toutes (Paris 10e, 14e… = centre de Paris)."""
        for r in lire_annonces()["rows"]:
            ville = "Paris" if r["dept"] == "75" else r["ville"]
            self.assertIn(f"{r['dept']}|{norm_ville(ville)}", COMMUNES, f"{r['_id']} : {r['ville']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
