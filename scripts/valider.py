"""Contrôle annonces.json et sa copie dans index.html.

Usage :
  python3 scripts/valider.py                    # contrôles du fichier seul
  python3 scripts/valider.py --base origin/main # + comparaison avec la version publiée

Avec --base, le script vérifie aussi que :
  - le code de index.html (hors données) est identique à la base ;
  - aucune annonce de la base n'a disparu ;
  - aucune annonce n'est passée en « vendu » ou en « L » sans autorisation / justificatif.
Les identifiants listés dans --autoriser (séparés par des virgules) peuvent être
supprimés ou passés en « vendu » : réservé aux décisions explicites du propriétaire.

Code de sortie : 0 si tout est conforme, 1 sinon.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter

from commun import ANNONCES, DEPTS, ERP, INDEX, MODES, PARKING, STATUTS, code_index, donnees_index

CHAMPS = {
    "_id": str, "titre": str, "ville": str, "dept": str, "agence": str, "url": str,
    "notes": str, "erpDetail": str, "erp": str, "parking": str, "statut": str,
    "surface": int, "ajoute": int, "vu": str, "transports": list,
}


def git_show(ref, chemin):
    return subprocess.check_output(["git", "show", f"{ref}:{chemin}"], text=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", help="référence git à comparer (ex. origin/main)")
    p.add_argument("--autoriser", default="", help="_id dont la suppression ou le passage en « vendu » est validé")
    args = p.parse_args()
    autorises = {x for x in args.autoriser.split(",") if x}

    erreurs, alertes = [], []
    try:
        payload = json.loads(ANNONCES.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERREUR annonces.json n'est pas un JSON valide : {e}")
        return 1
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list) or not isinstance(payload.get("date"), str):
        print("ERREUR structure attendue : {\"date\": \"JJ/MM/AAAA\", \"rows\": [...]}")
        return 1
    if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", payload["date"]):
        erreurs.append(f"date « {payload['date']} » : format JJ/MM/AAAA attendu")
    rows = payload["rows"]

    for i, r in enumerate(rows):
        ref = r.get("_id", f"ligne {i}")
        for champ, typ in CHAMPS.items():
            if not isinstance(r.get(champ), typ):
                erreurs.append(f"{ref} : champ « {champ} » manquant ou de type incorrect")
        if not (r.get("adresse") is None or isinstance(r.get("adresse"), str)):
            erreurs.append(f"{ref} : « adresse » doit être un texte ou null")
        if not (r.get("prix") is None or isinstance(r.get("prix"), int)):
            erreurs.append(f"{ref} : « prix » doit être un entier ou null")
        if r.get("dept") not in DEPTS:
            erreurs.append(f"{ref} : département « {r.get('dept')} » hors Île-de-France")
        for champ, valeurs in (("erp", ERP), ("parking", PARKING), ("statut", STATUTS)):
            if r.get(champ) not in valeurs:
                erreurs.append(f"{ref} : {champ} « {r.get(champ)} » non reconnu par le site ({', '.join(valeurs)})")
        for t in r.get("transports") or []:
            if t.get("mode") not in MODES:
                erreurs.append(f"{ref} : mode de transport « {t.get('mode')} » non reconnu ({', '.join(MODES)})")
            if not (t.get("distance") is None or isinstance(t.get("distance"), int)):
                erreurs.append(f"{ref} : distance de transport non entière")
        if isinstance(r.get("ajoute"), int) and r["ajoute"] < 10**12:
            erreurs.append(f"{ref} : « ajoute » ({r['ajoute']}) n'est pas un horodatage en millisecondes")
        if isinstance(r.get("vu"), str) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["vu"]):
            erreurs.append(f"{ref} : « vu » doit être au format AAAA-MM-JJ")
        if isinstance(r.get("url"), str) and not r["url"].startswith("https://"):
            erreurs.append(f"{ref} : URL invalide")

    for champ in ("_id", "url"):
        doublons = [k for k, n in Counter(r.get(champ) for r in rows).items() if n > 1]
        if doublons:
            erreurs.append(f"{champ} en double : {', '.join(map(str, doublons))}")
    refs = Counter((r.get("agence", "").lower(), r.get("ref")) for r in rows if r.get("ref"))
    for (agence, ref), n in refs.items():
        if n > 1:
            alertes.append(f"même référence « {ref} » ({agence}) sur {n} annonces")

    # Type L : « L » exige une source écrite. Les annonces déjà publiées sans source sont signalées sans être modifiées.
    for r in rows:
        if r.get("erp") == "L" and not r.get("erpSource"):
            alertes.append(f"{r.get('_id')} : classée « Type L confirmé » sans erpSource (statut conservé, à documenter)")

    html = INDEX.read_text(encoding="utf-8")
    if donnees_index(html) != payload:
        erreurs.append("la copie des données dans index.html ne correspond pas à annonces.json (lancer scripts/sync_index.py)")

    if args.base:
        base_html = git_show(args.base, "index.html")
        if code_index(base_html) != code_index(html):
            erreurs.append(f"le code de index.html (hors données) a changé par rapport à {args.base}")
        base = {r["_id"]: r for r in json.loads(git_show(args.base, "annonces.json"))["rows"]}
        actuels = {r["_id"]: r for r in rows}
        for i in base:
            if i not in actuels and i not in autorises:
                erreurs.append(f"{i} : annonce présente sur {args.base} mais supprimée sans autorisation")
        for i, r in actuels.items():
            avant = base.get(i, {})
            if r["statut"] == "vendu" and avant.get("statut") != "vendu" and i not in autorises:
                erreurs.append(f"{i} : passée en « vendu » (masquée du site) sans autorisation")
            if r["erp"] == "L" and avant.get("erp") != "L" and not r.get("erpSource"):
                erreurs.append(f"{i} : classée « Type L confirmé » sans justificatif (champ « erpSource »)")
            if r["erp"] == "L" and avant.get("erp") != "L" and not re.search(r"[Tt]ypes?\s+(?:[A-Z]{1,2}\s*(?:,|et)\s*)*L\b|\bERP\s+L\b", r.get("erpSource") or ""):
                erreurs.append(f"{i} : « erpSource » ne cite pas explicitement le type L")
            if avant and r["erp"] != avant.get("erp") and i not in autorises:
                erreurs.append(f"{i} : statut ERP modifié ({avant.get('erp')} → {r['erp']}) : seule une décision du propriétaire le permet")
        nouvelles = len([i for i in actuels if i not in base])
        print(f"Comparaison avec {args.base} : {len(base)} annonces avant, {len(actuels)} après, {nouvelles} nouvelles")

    print(f"{len(rows)} annonces, {len({r.get('_id') for r in rows})} identifiants uniques, relevé du {payload['date']}")
    for a in alertes:
        print("ALERTE", a)
    for e in erreurs:
        print("ERREUR", e)
    print("Validation : OK" if not erreurs else f"Validation : {len(erreurs)} erreur(s)")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
