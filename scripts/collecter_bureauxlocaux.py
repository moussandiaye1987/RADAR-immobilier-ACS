"""Collecte les annonces de vente BureauxLocaux des 8 départements d'Île-de-France.

Usage : python3 scripts/collecter_bureauxlocaux.py [--sortie veille/.candidats.json] [--pages-max 20]

Lit les pages de recherche listées dans veille/sources.json (département × type de bien,
pagination « /page/N »), extrait les données structurées de chaque page (bloc
<script id="react-context">) et écrit la liste des annonces candidates :
  - en vente, dans un des 8 départements, surface ≥ 150 m², prix ≤ 6 M€ ou sur demande ;
  - « connue » = déjà présente dans annonces.json (même numéro d'annonce BureauxLocaux) ;
  - « mots_cles » = indices d'usage ERP / salle relevés dans le titre et la description ;
  - « doublon_possible » = annonce du radar ou autre candidate de même département,
    surface à ±3 % et prix égal à ±3 % (même bien publié sous un autre numéro ou par une autre agence) ;
  - « examinee » = déjà étudiée lors d'une veille précédente (veille/examinees.json) ;
  - « score » = priorité d'examen (indices forts, puis adéquation aux filtres par défaut du site).
Les candidates sont triées : non connues et non examinées d'abord, par score décroissant.
Ce n'est qu'un tri préalable : chaque candidate retenue doit ensuite être lue et vérifiée
(voir veille/CONSIGNES.md). Le script ne modifie pas annonces.json.
"""
import argparse
import html
import json
import re
import time
import unicodedata

from commun import DEPTS, RACINE, lire_annonces, telecharger

SOURCES = RACINE / "veille" / "sources.json"
EXAMINEES = RACINE / "veille" / "examinees.json"
CONTEXTE = re.compile(r'<script type="text/json" id="react-context">(.*?)</script>', re.S)
NUMERO = re.compile(r"--(\d+)/?$")
MOTS_CLES = re.compile(
    r"\bERP\b|salle|réception|reception|spectacle|séminaire|seminaire|réunion|événement|evenement|"
    r"polyvalent|culte|cinéma|théâtre|theatre|discoth|restaurant|banquet|conférence|conference|"
    r"type L\b|catégorie [1-5]|accueil du public|recevant du public", re.I)
# Indices qui désignent directement un usage de salle (les autres, comme « ERP » ou
# « restaurant », sont fréquents dans les annonces de commerces et pèsent moins).
FORTS = re.compile(r"salle|réception|reception|spectacle|séminaire|seminaire|événement|evenement|polyvalent|"
                   r"culte|cinéma|théâtre|theatre|discoth|banquet|conférence|conference|type l", re.I)


def ville_norm(v):
    v = unicodedata.normalize("NFD", (v or "").lower())
    return re.sub(r"[^a-z]", "", "".join(ch for ch in v if not unicodedata.combining(ch)))


def proches(a, b):
    """Même bien probable : même département et surface à ±3 %, puis soit même ville
    (prix à ±3 % ou inconnu d'un côté), soit prix quasi identique (±1 %) dans une autre commune."""
    if a["dept"] != b["dept"] or not a["surface"] or not b["surface"]:
        return False
    if abs(a["surface"] - b["surface"]) > 0.03 * max(a["surface"], b["surface"]):
        return False
    if a["prix"] is None or b["prix"] is None:
        return ville_norm(a["ville"]) == ville_norm(b["ville"])
    ecart = abs(a["prix"] - b["prix"]) / max(a["prix"], b["prix"])
    return ecart <= (0.03 if ville_norm(a["ville"]) == ville_norm(b["ville"]) else 0.01)


def score(c):
    forts = sum(1 for k in c["mots_cles"] if FORTS.search(k))
    dans_filtres = (c["surface"] or 0) >= 250 and (c["prix"] is None or 300_000 <= c["prix"] <= 2_000_000)
    return forts * 3 + (len(c["mots_cles"]) - forts) + (2 if dans_filtres else 0)


def nombre(v):
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return None
    return n or None


def texte(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sortie", default=str(RACINE / "veille" / ".candidats.json"))
    p.add_argument("--pages-max", type=int, default=20)
    args = p.parse_args()

    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["bureauxlocaux"]
    examinees = json.loads(EXAMINEES.read_text(encoding="utf-8")) if EXAMINEES.exists() else {}
    radar = lire_annonces()["rows"]
    connus = {m.group(1) for r in radar if (m := NUMERO.search(r["url"]))}
    candidats, vus, erreurs = {}, 0, []

    for dept, slug in sources["departements"].items():
        for type_bien in sources["types"]:
            page, total = 1, 1
            while page <= min(total, args.pages_max):
                url = f"{sources['base']}/{slug}/{type_bien}" + (f"/page/{page}" if page > 1 else "")
                code, _, corps = telecharger(url)
                m = CONTEXTE.search(corps)
                if code != 200 or not m:
                    erreurs.append(f"{url} : HTTP {code}{'' if m else ', données introuvables'}")
                    break
                res = json.loads(m.group(1))["global"]["results"]
                total = res["pagination"]["total_pages"]
                for it in res["items"]:
                    vus += 1
                    num = str(it["id"])
                    cp = it.get("zip_code") or ""
                    surface = nombre(it.get("total_surface"))
                    prix = None if it.get("hide_price") else nombre(it.get("sale_price"))
                    if not it.get("is_sale") or cp[:2] not in DEPTS or (surface or 0) < 150 or (prix or 0) > 6_000_000:
                        continue
                    desc = texte(it.get("description"))
                    contacts = it.get("contacts_to_display") or [{}]
                    candidats.setdefault(num, {
                        "numero": num,
                        "url": "https://www.bureauxlocaux.com" + it["url"],
                        "titre": texte(it.get("label")),
                        "ville": it.get("city"), "cp": cp, "dept": cp[:2],
                        "adresse": it.get("new_display_address") or "",
                        "prix": prix, "surface": surface,
                        "agence": contacts[0].get("customer_trade_name", ""),
                        "occupe": bool((it.get("characteristics_json") or {}).get("is_occupied")),
                        "type": type_bien,
                        "connue": num in connus,
                        "examinee": num in examinees,
                        "mots_cles": sorted({k.lower() for k in MOTS_CLES.findall(it.get("label", "") + " " + desc)}),
                        "description": desc[:2000],
                    })
                page += 1
                time.sleep(1)

    for c in candidats.values():
        c["score"] = score(c)
        c["doublon_possible"] = [] if c["connue"] else (
            [r["_id"] for r in radar if proches(c, r)]
            + [o["numero"] for o in candidats.values() if o is not c and proches(c, o)])
    liste = sorted(candidats.values(), key=lambda c: (c["connue"], c["examinee"], -c["score"], c["dept"]))
    with open(args.sortie, "w", encoding="utf-8") as f:
        json.dump({"annonces_lues": vus, "erreurs": erreurs, "candidats": liste}, f, ensure_ascii=False, indent=1)
    a_examiner = [c for c in liste if not c["connue"] and not c["examinee"]]
    print(f"{vus} annonces lues, {len(liste)} dans les critères larges, "
          f"{sum(c['connue'] for c in liste)} déjà sur le radar, {sum(c['examinee'] and not c['connue'] for c in liste)} déjà examinées, "
          f"{len(a_examiner)} à examiner dont {sum(1 for c in a_examiner if c['score'] >= 3)} prioritaires (score ≥ 3)")
    for e in erreurs:
        print("ERREUR", e)
    print("Résultat :", args.sortie)


if __name__ == "__main__":
    main()
