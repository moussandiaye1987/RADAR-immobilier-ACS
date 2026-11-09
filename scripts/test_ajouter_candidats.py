"""Tests de scripts/ajouter_candidats.py, de la migration Type V et de valider.py (aucun réseau).

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
    base = {"numero": "90000001", "url": "https://www.bureauxlocaux.com/annonce/test-culte--90000001", "titre": "Local commercial à vendre",
            "ville": "Testville", "cp": "77000", "dept": "77", "adresse": "77000 Testville", "prix": 900000, "surface": 500,
            "agence": "Agence Test", "occupe": False, "type": "vente-commerces", "connue": False, "examinee": False,
            "description": "Vente des murs d'un lieu de culte de 500 m² en rez-de-chaussée, parking privatif de 20 places.",
            "score": 10, "doublon_possible": []}
    base.update(kw)
    return base


def num(i):
    return {"numero": str(i), "url": f"https://www.bureauxlocaux.com/annonce/t--{i}", "ville": f"Ville{i}"}


def lancer(cands, **kw):
    payload = lire_annonces()
    return A.executer(cands, copy.deepcopy(payload), {}, "2026-11-09", kw.get("max", 10), 1791500000000,
                      kw.get("max_transfo", 3)), payload


class Regles(unittest.TestCase):
    def test_ajout_lieu_de_culte(self):
        (s, ex, d), avant = lancer([cand()])
        self.assertEqual(len(s["rows"]), len(avant["rows"]) + 1)
        r = s["rows"][-1]
        self.assertEqual((r["dept"], r["prix"], r["surface"], r["statut"]), ("77", 900000, 500, "en_vente"))
        self.assertEqual((r["typeV"], r["profil"], r["erp"]), ("potentiel", "culte_existant", "verifier"))
        self.assertEqual(r["parking"], "sur_place")
        self.assertEqual((r["transports"], r["adresse"]), ([], ""))
        self.assertTrue(r["nouveau"])
        self.assertEqual(r["_id"], "testville-culte-500")
        self.assertEqual(s["date"], "09/11/2026")
        self.assertIn(r["_id"], d["ajoutees"])

    # --- Profils recherchés ------------------------------------------------------------------
    def test_profils(self):
        cas = {
            "Ancienne église désaffectée de 500 m², nef et sacristie.": "ancien_religieux",
            "Ancien presbytère avec grande salle au rez-de-chaussée.": "ancien_religieux",
            "Salle des fêtes anciennement occupée par une association évangélique.": "ancien_religieux",
            "Local occupé jusqu'ici par une salle de prière, 500 m².": "culte_existant",
            "Local associatif de 500 m² avec accueil.": "associatif",
            "Salle de réception de 500 m², cuisine traiteur.": "salle",
        }
        for desc, profil in cas.items():
            (s, _, _), avant = lancer([cand(description=desc)])
            self.assertEqual(len(s["rows"]), len(avant["rows"]) + 1, desc)
            self.assertEqual(s["rows"][-1]["profil"], profil, desc)
            self.assertEqual(s["rows"][-1]["typeV"], "potentiel", desc)

    def test_faux_positifs_noms_de_lieux(self):
        for ville, desc in (("Savigny-le-Temple", "Local d'activités de 500 m² à Savigny-le-Temple."),
                            ("Savigny-le-Temple", "Local d'activités de 500 m² à SAVIGNY LE TEMPLE, ZI."),
                            ("Pantin", "Local d'activités. Métro Église de Pantin (ligne 5)."),
                            ("Testville", "Entrepôt situé rue de l'Église, 500 m² de stockage."),
                            ("Testville", "Entrepôt à deux pas de l'église, stockage."),
                            ("Testville", "Local d'activités face à la mosquée, stockage.")):
            (s, _, _), avant = lancer([cand(ville=ville, description=desc, type="vente-entrepots")])
            self.assertEqual(len(s["rows"]), len(avant["rows"]), desc)

    def test_priorite_culte_avant_salle_et_transformation(self):
        salle = cand(**num(90000003), score=99, description="Salle de réception de 500 m².")
        transfo = cand(**num(90000004), score=99, description="Grand local ERP de plain-pied, 500 m².")
        evoque = cand(**num(90000005), score=50, description="Local de 500 m² idéal pour un lieu de culte ou une association.")
        culte = cand(**num(90000006), score=1)
        (s, _, d), avant = lancer([salle, transfo, evoque, culte], max=2)
        ajout = [r["ville"] for r in s["rows"][len(avant["rows"]):]]
        self.assertEqual(ajout, ["Ville90000006", "Ville90000005"])     # culte décrit, puis culte évoqué
        self.assertEqual(d["reportees_plafond"], 2)

    def test_usage_evoque(self):
        (s, _, _), _ = lancer([cand(titre="Local", description="Local de 500 m² pouvant convenir à un lieu de culte.")])
        r = s["rows"][-1]
        self.assertEqual((r["typeV"], r["profil"]), ("potentiel", "culte_existant"))
        self.assertIn("évoqué", r["titre"])

    def test_transformation_et_plafond(self):
        cs = [cand(**num(90000020 + i), surface=400 + 10 * i, type="vente-entrepots",
                   description="Local d'activités de plain-pied, ERP, hauteur 6 m.") for i in range(5)]
        (s, _, d), avant = lancer(cs, max_transfo=2)
        nouv = s["rows"][len(avant["rows"]):]
        self.assertEqual(len(nouv), 2)
        self.assertTrue(all(r["profil"] == "transformation" and r["typeV"] == "potentiel" for r in nouv))
        self.assertEqual(d["reportees_plafond"], 3)
        # sans indice ERP / public ou sans plain-pied : hors périmètre
        for desc in ("Entrepôt de plain-pied, hauteur 8 m.", "Local ERP au 2e étage."):
            (s, _, _), avant = lancer([cand(description=desc, type="vente-entrepots")])
            self.assertEqual(len(s["rows"]), len(avant["rows"]), desc)

    # --- Statuts Type V ----------------------------------------------------------------------
    def test_type_v_explicite_avec_citation(self):
        desc = "Lieu de culte de 500 m². Établissement classé ERP de type V, catégorie 3."
        (s, _, _), _ = lancer([cand(description=desc)])
        r = s["rows"][-1]
        self.assertEqual(r["typeV"], "V")
        self.assertIn("ERP de type V", r["typeVSource"])
        self.assertIn(r["url"], r["typeVSource"])

    def test_type_v_jamais_sans_justificatif(self):
        base = "Lieu de culte de 500 m². "
        for phrase in ("Ancienne église : type V probable.",
                       "Possibilité de classement en ERP de type V.",
                       "Local transformable en ERP type V après travaux.",
                       "Classement ERP type V à confirmer.",
                       "Le local n'est pas classé ERP type V.",
                       "Types L ou V selon l'exploitation.",
                       "Classement L/V à confirmer.",
                       "Idéal pour un ERP de type V.",
                       "Ancienne chapelle désaffectée.",
                       "ERP 5e catégorie."):
            (s, _, _), _ = lancer([cand(description=base + phrase)])
            self.assertNotEqual(s["rows"][-1]["typeV"], "V", phrase)
            self.assertNotIn("typeVSource", s["rows"][-1], phrase)

    def test_salle_type_l_existante(self):
        (s, _, _), _ = lancer([cand(description="Salle de réception de 500 m². Classée ERP type L, catégorie 3.")])
        r = s["rows"][-1]
        self.assertEqual((r["typeV"], r["erp"], r["profil"]), ("L", "L", "salle"))
        self.assertIn("type L", r["erpSource"])
        for phrase in ("Possibilité de type L.", "Types M ou L.", "Classement N/L à confirmer."):
            (s, _, _), _ = lancer([cand(description="Salle de réception de 500 m². " + phrase)])
            self.assertEqual((s["rows"][-1]["typeV"], s["rows"][-1]["erp"]), ("potentiel", "verifier"), phrase)

    def test_type_l_explicite_seul_suffit(self):
        (s, _, _), avant = lancer([cand(titre="Local", description="Local d'activité 500 m². Classé ERP type L.")])
        self.assertEqual(len(s["rows"]), len(avant["rows"]) + 1)
        self.assertEqual(s["rows"][-1]["typeV"], "L")

    def test_statuts_existants_preserves(self):
        (s, _, _), avant = lancer([cand(description="Lieu de culte classé ERP type V.")])
        anciens = {r["_id"]: (r["erp"], r.get("typeV"), r.get("archive")) for r in avant["rows"]}
        self.assertEqual({r["_id"]: (r["erp"], r.get("typeV"), r.get("archive")) for r in s["rows"] if r["_id"] in anciens}, anciens)

    # --- Données ambiguës et hors périmètre --------------------------------------------------
    def test_donnees_manquantes_ambigues(self):
        for champ, valeur in (("prix", None), ("agence", ""), ("ville", "")):
            (s, _, d), avant = lancer([cand(**{champ: valeur})])
            self.assertEqual(len(s["rows"]), len(avant["rows"]), champ)
            self.assertEqual(d["ambigues_total"], 1, champ)

    def test_hors_perimetre(self):
        for kw in ({"dept": "60"}, {"surface": 100}, {"prix": 9_000_000}, {"connue": True}, {"surface": None},
                   {"description": "Entrepôt de stockage 500 m²."}, {"description": "Appartement ancienne chapelle."}):
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
        a, b = cand(), cand(numero="90000002", url="https://www.bureauxlocaux.com/annonce/test-culte--90000002")
        (s, _, d), avant = lancer([a, b])
        self.assertEqual(len(s["rows"]), len(avant["rows"]) + 1)

    def test_plafond_et_ids_uniques(self):
        cs = [cand(**num(90000010 + i), surface=400 + 50 * i) for i in range(5)]
        (s, _, d), avant = lancer(cs, max=3)
        self.assertEqual(len(s["rows"]), len(avant["rows"]) + 3)
        self.assertEqual(d["reportees_plafond"], 2)
        ids = [r["_id"] for r in s["rows"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_vefa_bureaux_prix_incoherent_ambigus(self):
        for kw in ({"description": "Local pour lieu de culte en VEFA, livraison prévisionnelle 2027."}, {"type": "vente-bureaux"},
                   {"prix": 50000}):
            (s, _, d), avant = lancer([cand(**kw)])
            self.assertEqual(len(s["rows"]), len(avant["rows"]), kw)
            self.assertEqual(d["ambigues_total"], 1, kw)

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
        s2, _, d2 = A.executer([c], s, ex, "2026-11-10", 10, 1791600000000)
        self.assertEqual(len(s2["rows"]), n)
        self.assertEqual(d2["ajoutees"], [])


class Migration(unittest.TestCase):
    def test_donnees_migrees(self):
        rows = lire_annonces()["rows"]
        for r in rows:
            self.assertIn(r["typeV"], ("V", "potentiel", "L"), r["_id"])
            self.assertEqual(r["typeV"] == "L", r["erp"] == "L", r["_id"])
            self.assertNotEqual(r["typeV"], "V", r["_id"])            # aucune annonce existante ne cite le type V
            if r.get("archive"):
                self.assertTrue(r.get("archiveMotif"), r["_id"])
            self.assertTrue(r.get("analyseV"), r["_id"])

    def test_migration_idempotente(self):
        import migrer_type_v as M
        payload = copy.deepcopy(lire_annonces())
        self.assertEqual(M.migrer(payload)["migrees"], 0)


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
        """valider.py : statuts ERP et Type V (justificatifs, modifications d'annonces existantes, archivage)."""
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
                for k in ("erpSource", "typeVSource", "archive", "archiveMotif", "archiveDate"):
                    r.pop(k, None)
                r.update({"_id": "nouveau-test", "url": "https://example.org/x", "erp": "verifier", "typeV": "potentiel", **kw})
                return r

            self.assertEqual(valider().returncode, 0)
            appliquer(lambda rows: rows.append(nouvelle()))
            self.assertEqual(valider().returncode, 0, "une nouvelle annonce « verifier » doit être acceptée")
            git("checkout", "-q", "."), git("clean", "-fdq")
            appliquer(lambda rows: rows.append(nouvelle(erp="L", typeV="L")))
            self.assertEqual(valider().returncode, 1, "« L » sans erpSource doit être refusé")
            git("checkout", "-q", "."), git("clean", "-fdq")
            appliquer(lambda rows: rows.append(nouvelle(erp="L", typeV="L", erpSource="« Local pour ERP » — https://example.org/x")))
            self.assertEqual(valider().returncode, 1, "« L » dont la source ne cite pas le type L doit être refusé")
            git("checkout", "-q", "."), git("clean", "-fdq")
            appliquer(lambda rows: rows.append(nouvelle(erp="L", typeV="L", erpSource="« Classé ERP type L » — https://example.org/x")))
            self.assertEqual(valider().returncode, 0, "« L » avec citation explicite doit être accepté")
            git("checkout", "-q", "."), git("clean", "-fdq")
            appliquer(lambda rows: rows[0].update(erp="L" if rows[0]["erp"] != "L" else "verifier"))
            self.assertEqual(valider().returncode, 1, "modifier le statut d'une annonce existante doit être refusé")
            # --- Type V ---
            for modif, attendu, message in (
                    (lambda rows: rows.append(nouvelle(typeV="V")), 1, "« V » sans justificatif doit être refusé"),
                    (lambda rows: rows.append(nouvelle(typeV="V", typeVSource="« Ancienne église » — https://example.org/x")), 1,
                     "« V » dont la source ne cite pas le type V doit être refusé"),
                    (lambda rows: rows.append(nouvelle(typeV="V", typeVSource="« Classé ERP de type V » — https://example.org/x")), 0,
                     "« V » avec citation explicite doit être accepté"),
                    (lambda rows: rows.append(nouvelle(typeV="L")), 1, "« Salle Type L existante » sans erp L doit être refusé"),
                    (lambda rows: rows.append(nouvelle(typeV="X")), 1, "statut Type V inconnu refusé"),
                    (lambda rows: rows.append(nouvelle(profil="autre")), 1, "profil inconnu refusé"),
                    (lambda rows: rows.append(nouvelle(archive=True)), 1, "archivage sans motif refusé"),
                    (lambda rows: next(r for r in rows if r["typeV"] == "potentiel").update(typeV="V", typeVSource="« ERP type V » — x"), 1,
                     "passer une annonce existante en « V » doit être refusé"),
                    (lambda rows: next(r for r in rows if not r.get("archive")).update(archive=True, archiveMotif="test"), 1,
                     "archiver une annonce existante sans autorisation doit être refusé"),
                    (lambda rows: rows.pop(0), 1, "supprimer une annonce doit être refusé")):
                git("checkout", "-q", "."), git("clean", "-fdq")
                appliquer(modif)
                self.assertEqual(valider().returncode, attendu, message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
