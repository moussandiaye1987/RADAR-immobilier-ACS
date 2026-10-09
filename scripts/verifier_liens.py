"""Vérifie le lien de chaque annonce et tient à jour veille/etat_liens.json.

Usage : python3 scripts/verifier_liens.py [--date AAAA-MM-JJ]

Statuts :
  ok              la page de l'annonce répond normalement
  retiree         le site répond 404/410 ou indique que l'annonce n'existe plus
  retiree_probable  BureauxLocaux redirige vers une page de recherche (annonce sans doute retirée)
  redirigee       redirection vers une autre annonce : à vérifier à la main
  non_verifiable  site protégé contre les robots (PAP, SeLoger…) : impossible à contrôler
  erreur          autre réponse (délai, erreur serveur) : à revérifier au prochain passage

Ce script ne modifie jamais annonces.json : il ne fait que signaler.
« depuis » garde la date du premier contrôle en échec consécutif, pour juger d'une
indisponibilité durable (plusieurs jours de suite) avant de proposer une décision.
"""
import argparse
import datetime
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from commun import RACINE, lire_annonces, telecharger

ETAT = RACINE / "veille" / "etat_liens.json"
ANTI_ROBOT = re.compile(r"datadome|captcha|just a moment|un instant…|cf-chl|access denied", re.I)
RETIREE = re.compile(r"n'est plus disponible|n.existe plus|plus en ligne|a été retirée|annonce expirée|annonce désactivée", re.I)


def classer(url):
    code, finale, corps = telecharger(url)
    if code == 403 and ANTI_ROBOT.search(corps[:20000]):
        return "non_verifiable", code, finale
    if code in (404, 410) or (code == 200 and RETIREE.search(corps[:50000])):
        return "retiree", code, finale
    if code == 200 and finale.rstrip("/") != url.rstrip("/"):
        chemin = urlparse(finale).path
        if "bureauxlocaux.com" in finale and chemin.startswith("/immobilier-d-entreprise/annonces/"):
            return "retiree_probable", code, finale
        return "redirigee", code, finale
    if code == 200:
        return "ok", code, finale
    return "erreur", code, finale


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=datetime.date.today().isoformat())
    args = p.parse_args()

    rows = lire_annonces()["rows"]
    precedent = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}

    def controle(r):
        time.sleep(0.5)  # rester raisonnable avec les sites
        return r, classer(r["url"])

    with ThreadPoolExecutor(4) as ex:
        resultats = list(ex.map(controle, rows))

    etat = {}
    for r, (statut, code, finale) in resultats:
        avant = precedent.get(r["_id"], {})
        depuis = None if statut == "ok" else (avant.get("depuis") if avant.get("statut") not in (None, "ok") else args.date)
        etat[r["_id"]] = {"statut": statut, "code": code, "url": r["url"], "url_finale": finale,
                          "depuis": depuis, "controle": args.date}
    ETAT.parent.mkdir(exist_ok=True)
    ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")

    compte = {}
    for e in etat.values():
        compte[e["statut"]] = compte.get(e["statut"], 0) + 1
    print("Liens contrôlés :", ", ".join(f"{k} {v}" for k, v in sorted(compte.items())))
    for i, e in sorted(etat.items()):
        if e["statut"] != "ok":
            print(f"- {i} : {e['statut']} (HTTP {e['code']}, depuis le {e['depuis']}) {e['url_finale']}")


if __name__ == "__main__":
    main()
