"""Tests de scripts/ajouter_candidats.py (aucun réseau).

Usage : python3 scripts/test_ajouter_candidats.py
"""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ajouter_candidats as A  # noqa: E402
from commun import RACINE, lire_annonces  # noqa: E402


def cand(**kw):
    base = {"numero": "90000001", "url": "https://www.bureauxlocaux.com/annonce/test-salle--90000001", "titre": "Lieu de réception à vendre",
            "ville": "Testville", "cp": "77000", "dept": "77", "adresse": "77000 Testville", "prix": 900000, "surface": 500,
            "agence": "Agence Test", "occupe": False, "type": "vente-commerces", "connue": False, "examinee": False,
            "description": "Vente murs d'un lieu de réception avec 2 salles de réception et parking privatif de 20 places.",
            "score": 10, "doublon_possible": []}
    base.update(kw)
    return base


def lancer(cands, **kw):
    payload = lire_annonces()
    return A.executer(cands, copy.deepcopy(payload), {}, "2026-10-09", kw.get("max", 10), 1791500000000), payload


class Regles(unittest.TestCase):
    def test_ajout_fiable(self):
        (s, ex, d), avant = lancer([cand()])
        self.assertEqual(len(s["rows"]), len(avant["rows"]) + 1)
        r = s["rows"][-1]
        self.assertEqual((r["dept"], r["prix"], r["surface"], r["statut"]), ("77", 900000, 500, "en_vente"))
        self.assertEqual(r["parking"], "sur_place")
        self.assertEqual(r["transports"], [])
        self.assertEqual(r["adresse"], "")
        self.assertTrue(r["nouveau"])
        self.assertEqual(s["date"], "09/10/2026")
        self.assertIn(r["_id"], d["ajoutees"])

    # --- Statuts ERP -------------------------------------------------------------------------
    def test_statut_par_defaut_erp_a_verifier(self):
        for desc in ("Lieu de réception de 500 m².",
                     "Lieu de réception de 500 m², local conforme aux normes ERP catégorie 5.",
                     "Lieu de réception de 500 m², ERP sur demande."):
            (s, _, _), _ = lancer([cand(description=desc)])
            r = s["rows"][-1]
            self.assertEqual(r["erp"], "verifier", desc)           # affiché « ERP à vérifier »
            self.assertNotIn("erpSource", r)
            self.assertIn("Type L non confirmé", r["erpDetail"])

    def test_type_l_explicite_est_identifie_avec_citation(self):
        desc = "Salle de réception de 500 m². Établissement classé ERP de type L, catégorie 4."
        (s, _, _), _ = lancer([cand(description=desc)])
        r = s["rows"][-1]
        self.assertEqual(r["erp"], "L")
        self.assertIn("ERP de type L", r["erpSource"])
        self.assertIn(r["url"], r["erpSource"])

    def test_type_l_jamais_sur_supposition(self):
        base = "Salle de réception de 500 m². "
        for phrase in ("Possibilité de classement en ERP de type L.",
                       "Local transformable en ERP type L après travaux.",
                       "Classement ERP type L à confirmer.",
                       "Le local n'est pas classé ERP type L.",
                       "Aménageable en ERP type L sur demande.",
                       "Types M ou L selon l'exploitation.",
                       "Classement exact N/L à confirmer.",
                       "ERP sur demande. Idéal pour un lieu de type L.",
                       "Salle polyvalente idéale pour événements."):
            (s, _, _), _ = lancer([cand(description=base + phrase)])
            self.assertEqual(s["rows"][-1]["erp"], "verifier", phrase)
            self.assertNotIn("erpSource", s["rows"][-1], phrase)

    def test_type_l_explicite_seul_suffit_comme_interet(self):
        desc = "Local d'activité 500 m². Classé ERP type L."
        (s, _, d), avant = lancer([cand(titre="Local", description=desc)])
        self.assertEqual(len(s["rows"]), len(avant["rows"]) + 1)
        self.assertEqual(s["rows"][-1]["erp"], "L")

    def test_aucun_statut_autre_que_les_trois_connus(self):
        (s, _, _), avant = lancer([cand(), cand(numero="90000002", url="https://www.bureauxlocaux.com/annonce/x--90000002",
                                                ville="Autre", description="Salle des fêtes classée ERP type L.")])
        for r in s["rows"][len(avant["rows"]):]:
            self.assertIn(r["erp"], ("L", "ERP", "verifier"))
            if r["erp"] == "L":
                self.assertTrue(r.get("erpSource"))

    def test_usage_evoque_publie_a_verifier_apres_les_usages_decrits(self):
        evoque = cand(numero="90000003", url="https://www.bureauxlocaux.com/annonce/e--90000003", ville="Evoque", score=99,
                      titre="Local", description="Local idéal pour une salle de réception ou un séminaire.")
        decrit = cand(numero="90000004", url="https://www.bureauxlocaux.com/annonce/d--90000004", ville="Decrit", score=1)
        (s, _, d), avant = lancer([evoque, decrit], max=1)
        self.assertEqual(len(s["rows"]), len(avant["rows"]) + 1)
        self.assertEqual(s["rows"][-1]["ville"], "Decrit")          # l'usage décrit passe avant l'usage évoqué
        self.assertEqual(d["reportees_plafond"], 1)
        (s, _, _), avant = lancer([evoque])
        r = s["rows"][-1]
        self.assertEqual((r["erp"], len(s["rows"])), ("verifier", len(avant["rows"]) + 1))
        self.assertIn("évoqué", r["titre"])

    def test_statuts_existants_preserves(self):
        (s, _, _), avant = lancer([cand(description="Salle des fêtes classée ERP type L.")])
        anciens = {r["_id"]: r["erp"] for r in avant["rows"]}
        self.assertEqual({r["_id"]: r["erp"] for r in s["rows"] if r["_id"] in anciens}, anciens)

    def test_donnees_manquantes_ambigues(self):
        for champ, valeur in (("prix", None), ("agence", ""), ("ville", "")):
            (s, _, d), avant = lancer([cand(**{champ: valeur})])
            self.assertEqual(len(s["rows"]), len(avant["rows"]), champ)
            self.assertEqual(d["ambigues_total"], 1, champ)

    def test_hors_perimetre(self):
        for kw in ({"dept": "60"}, {"surface": 100}, {"prix": 9_000_000}, {"connue": True}, {"surface": None}):
            (s, _, d), avant = lancer([cand(**kw)])
            self.assertEqual(len(s["rows"]), len(avant["rows"]), kw)

    def test_doublon_avec_radar(self):
        existante = lire_annonces()["rows"][0]
        c = cand(ville=existante["ville"], dept=existante["dept"], surface=existante["surface"], prix=existante["prix"])
        (s, _, d), avant = lancer([c])
        self.assertEqual(len(s["rows"]), len(avant["rows"]))
        self.assertTrue(any("même bien" in m for a in d["ambigues_non_publiees"] for m in a["motifs"]))

    def test_doublon_possible_et_numero_deja_present(self):
        (s, _, d), avant = lancer([cand(doublon_possible=["123"])])
        self.assertEqual(len(s["rows"]), len(avant["rows"]))
        existante = lire_annonces()["rows"][0]
        (s, _, d), avant = lancer([cand(url=existante["url"])])
        self.assertEqual(len(s["rows"]), len(avant["rows"]))

    def test_doublon_entre_candidates(self):
        a, b = cand(), cand(numero="90000002", url="https://www.bureauxlocaux.com/annonce/test-salle--90000002")
        (s, _, d), avant = lancer([a, b])
        self.assertEqual(len(s["rows"]), len(avant["rows"]) + 1)

    def test_plafond_et_ids_uniques(self):
        cs = [cand(numero=str(90000010 + i), url=f"https://www.bureauxlocaux.com/annonce/t--{90000010 + i}",
                   surface=400 + 50 * i, ville=f"Ville{i}") for i in range(5)]
        (s, _, d), avant = lancer(cs, max=3)
        self.assertEqual(len(s["rows"]), len(avant["rows"]) + 3)
        self.assertEqual(d["reportees_plafond"], 2)
        ids = [r["_id"] for r in s["rows"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_vefa_et_bureaux_et_prix_incoherent_ambigus(self):
        for kw in ({"description": "Lieu de réception en VEFA, livraison prévisionnelle 2027."}, {"type": "vente-bureaux"},
                   {"prix": 50000}):
            (s, _, d), avant = lancer([cand(**kw)])
            self.assertEqual(len(s["rows"]), len(avant["rows"]), kw)

    def test_faux_positifs_transports(self):
        (s, _, _), avant = lancer([cand(titre="Local", description="Métro Église de Pantin (ligne 5). Bus Théâtre de Saint-Maur.")])
        self.assertEqual(len(s["rows"]), len(avant["rows"]))

    def test_existantes_preservees(self):
        (s, _, _), avant = lancer([cand()])
        anciens = {r["_id"]: r for r in avant["rows"]}
        for r in s["rows"]:
            if r["_id"] in anciens:
                a, b = dict(anciens[r["_id"]]), dict(r)
                a.pop("nouveau", None), b.pop("nouveau", None)
                self.assertEqual(a, b)
        self.assertTrue(set(anciens) <= {r["_id"] for r in s["rows"]})

    def test_idempotence(self):
        (s, ex, _), _ = lancer([cand()])
        n = len(s["rows"])
        ajoutee = s["rows"][-1]
        c = cand(url=ajoutee["url"], connue=True)
        s2, _, d2 = A.executer([c], s, ex, "2026-10-10", 10, 1791600000000)
        self.assertEqual(len(s2["rows"]), n)
        self.assertEqual(d2["ajoutees"], [])


class Integration(unittest.TestCase):
    def test_cli_complet_dans_copie_temporaire(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            shutil.copytree(RACINE / "scripts", t / "scripts", ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
            (t / "veille").mkdir()
            for f in ("annonces.json", "index.html"):
                shutil.copy(RACINE / f, t / f)
            shutil.copy(RACINE / "veille" / "examinees.json", t / "veille" / "examinees.json")
            (t / "veille" / ".candidats.json").write_text(json.dumps({"annonces_lues": 1, "erreurs": [], "candidats": [cand()]}))
            avant = len(lire_annonces()["rows"])
            r = subprocess.run([sys.executable, str(t / "scripts" / "ajouter_candidats.py"), "--date", "2026-10-09"],
                               capture_output=True, text=True, cwd=t)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            data = json.loads((t / "annonces.json").read_text())
            self.assertEqual(len(data["rows"]), avant + 1)
            self.assertIn('"Testville"', (t / "index.html").read_text())
            self.assertTrue((t / "veille" / "diagnostic.json").exists())
            v = subprocess.run([sys.executable, str(t / "scripts" / "valider.py")], capture_output=True, text=True, cwd=t)
            self.assertEqual(v.returncode, 0, v.stdout)
            # candidates vides ou illisibles : échec explicite, rien n'est écrit
            (t / "veille" / ".candidats.json").write_text(json.dumps({"candidats": []}))
            r = subprocess.run([sys.executable, str(t / "scripts" / "ajouter_candidats.py")], capture_output=True, text=True, cwd=t)
            self.assertEqual(r.returncode, 1)

    def test_valider_controle_les_statuts_erp(self):
        """valider.py : « L » sans citation du type L refusé, statut existant modifié refusé, « verifier » accepté."""
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            shutil.copytree(RACINE / "scripts", t / "scripts", ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
            for f in ("annonces.json", "index.html"):
                shutil.copy(RACINE / f, t / f)
            git = lambda *a: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=t, check=True,
                                            capture_output=True)
            git("init", "-q", "-b", "base")
            git("add", "."), git("commit", "-qm", "base")

            def valider():
                return subprocess.run([sys.executable, str(t / "scripts" / "valider.py"), "--base", "base"],
                                      capture_output=True, text=True, cwd=t)

            def appliquer(modif):
                payload = json.loads((t / "annonces.json").read_text())
                modif(payload["rows"])
                (t / "annonces.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1))
                subprocess.run([sys.executable, str(t / "scripts" / "sync_index.py")], cwd=t, check=True, capture_output=True)

            def nouvelle(**kw):
                r = dict(lire_annonces()["rows"][0])
                r.pop("erpSource", None)
                r.update({"_id": "nouveau-test", "url": "https://example.org/x", "erp": "verifier", **kw})
                return r

            self.assertEqual(valider().returncode, 0)
            appliquer(lambda rows: rows.append(nouvelle()))
            self.assertEqual(valider().returncode, 0, "une nouvelle annonce « verifier » doit être acceptée")
            git("checkout", "-q", "."), git("clean", "-fdq")
            appliquer(lambda rows: rows.append(nouvelle(erp="L")))
            self.assertEqual(valider().returncode, 1, "« L » sans erpSource doit être refusé")
            git("checkout", "-q", "."), git("clean", "-fdq")
            appliquer(lambda rows: rows.append(nouvelle(erp="L", erpSource="« Local pour ERP » — https://example.org/x")))
            self.assertEqual(valider().returncode, 1, "« L » dont la source ne cite pas le type L doit être refusé")
            git("checkout", "-q", "."), git("clean", "-fdq")
            appliquer(lambda rows: rows.append(nouvelle(erp="L", erpSource="« Classé ERP type L » — https://example.org/x")))
            self.assertEqual(valider().returncode, 0, "« L » avec citation explicite doit être accepté")
            git("checkout", "-q", "."), git("clean", "-fdq")
            appliquer(lambda rows: rows[0].update(erp="L" if rows[0]["erp"] != "L" else "verifier"))
            self.assertEqual(valider().returncode, 1, "modifier le statut d'une annonce existante doit être refusé")


if __name__ == "__main__":
    unittest.main(verbosity=2)
