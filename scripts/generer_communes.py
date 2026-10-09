"""Génère data/communes_idf.json : centre approximatif de chaque commune d'Île-de-France.

Usage : python3 scripts/generer_communes.py [--source URL_OU_FICHIER]

Source : contours des communes d'Île-de-France (données IGN Admin Express, dépôt gregoiredavid/france-geojson,
licence ouverte). Le centre est le centre de gravité du plus grand polygone de la commune : c'est une position
APPROXIMATIVE de la commune, jamais l'adresse d'une annonce.
Sortie : {"<département>|<nom normalisé>": [latitude, longitude]}. La normalisation des noms est identique à celle
de la carte dans index.html (fonction normVille).
Ce script ne fait pas partie de la veille quotidienne : il n'est à relancer qu'en cas de besoin (fusion de communes…).
"""
import argparse
import json
import re
import unicodedata

from commun import RACINE, DEPTS, telecharger

SOURCE = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions/ile-de-france/communes-ile-de-france.geojson"
SORTIE = RACINE / "data" / "communes_idf.json"
# Noms d'usage ou nouveaux noms officiels absents du fichier de contours : « département|nom normalisé » -> même centre.
ALIAS = {"93|saintouensurseine": "93|saintouen", "91|evrycourcouronnes": "91|evry"}


def norm_ville(nom):
    """Même règle que normVille() dans index.html."""
    t = unicodedata.normalize("NFD", (nom or "").lower().replace("œ", "oe").replace("æ", "ae"))
    t = "".join(c for c in t if not unicodedata.combining(c))
    mots = [{"st": "saint", "ste": "sainte"}.get(m, m) for m in re.sub(r"[^a-z0-9]+", " ", t).split()]
    if len(mots) > 1 and mots[0] in ("le", "la", "les", "l"):   # « Les Mureaux » et « Mureaux (Les) » se confondent
        mots = mots[1:]
    return "".join(mots)


def centre_polygone(anneau):
    """Centre de gravité d'un anneau [[lng, lat], …] (formule de l'aire signée)."""
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(anneau, anneau[1:] + anneau[:1]):
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    if abs(a) < 1e-12:
        return anneau[0][0], anneau[0][1], 0.0
    return cx / (3 * a), cy / (3 * a), abs(a / 2)


def centre_commune(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    meilleur = max((centre_polygone(p[0]) for p in polys), key=lambda c: c[2])
    return meilleur[1], meilleur[0]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", default=SOURCE)
    args = p.parse_args()
    if args.source.startswith("http"):
        code, _, corps = telecharger(args.source, timeout=120)
        if code != 200:
            raise SystemExit(f"ERREUR téléchargement ({code}) : {args.source}")
    else:
        corps = open(args.source, encoding="utf-8").read()
    sortie = {}
    for f in json.loads(corps)["features"]:
        dept = f["properties"]["code"][:2]
        if dept not in DEPTS:
            continue
        lat, lng = centre_commune(f["geometry"])
        sortie[f"{dept}|{norm_ville(f['properties']['nom'])}"] = [round(lat, 4), round(lng, 4)]
    for alias, cible in ALIAS.items():
        if cible in sortie and alias not in sortie:
            sortie[alias] = sortie[cible]
    SORTIE.parent.mkdir(exist_ok=True)
    SORTIE.write_text(json.dumps(dict(sorted(sortie.items())), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(sortie)} communes écrites dans {SORTIE}")


if __name__ == "__main__":
    main()
