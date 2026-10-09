"""Ajoute automatiquement à annonces.json les candidates BureauxLocaux suffisamment fiables.

Usage :
  python3 scripts/ajouter_candidats.py [--candidats veille/.candidats.json] [--max-ajouts 10]
                                       [--date AAAA-MM-JJ] [--simulation]

Entrée : veille/.candidats.json, produit par scripts/collecter_bureauxlocaux.py.
Sorties (hors --simulation) : annonces.json et la copie de index.html (via commun.ecrire_annonces),
veille/examinees.json (annonces ajoutées) et veille/diagnostic.json (trace des annonces ambiguës).

Principes (aucun appel réseau, aucune IA : uniquement des règles) :
  - une candidate n'est ajoutée que si TOUS les critères « durs » sont remplis (en vente, 8 départements,
    surface ≥ 150 m², prix connu ≤ 6 M€, commune, agence, lien https) ET si l'annonce décrit elle-même un usage
    de salle (réception, spectacle, culte, cinéma, amphithéâtre, couverts…) dans une phrase non hypothétique ;
  - une candidate ambiguë (usage seulement « possible », doublon possible, cession de fonds, location,
    information incohérente) n'est PAS ajoutée : elle est consignée dans veille/diagnostic.json ;
  - aucune information n'est inventée : `erp` vaut « ERP » si l'annonce déclare un classement ERP, sinon
    « verifier » ; JAMAIS « L » (aucun justificatif de type L ne peut être établi par règle) ;
    transports et référence restent vides, le parking n'est renseigné que si l'annonce le cite ;
  - aucune annonce existante n'est modifiée, supprimée ni passée en « vendu » (seule l'étiquette
    « nouveau » est retirée après 7 jours, comme le prévoient les consignes) ;
  - au plus --max-ajouts annonces par exécution ; le reste est repris aux exécutions suivantes.
"""
import argparse
import datetime
import json
import re
import sys
import time
import unicodedata

from commun import DEPTS, RACINE, ecrire_annonces, lire_annonces

CANDIDATS = RACINE / "veille" / ".candidats.json"
EXAMINEES = RACINE / "veille" / "examinees.json"
DIAGNOSTIC = RACINE / "veille" / "diagnostic.json"

SURFACE_MIN = 150
PRIX_MAX = 6_000_000
ECART_DOUBLON = 0.03

# Usage de salle décrit par l'annonce : étiquette -> motif.
USAGES = {
    "réception": r"salles? de r[ée]ception|lieux? de r[ée]ception|salles? des f[êe]tes|salles? de banquet",
    "spectacle": r"salles? de spectacle|salles? de cin[ée]ma|anciens? (?:cin[ée]ma|th[ée][âa]tre)|ancienne? (?:salle de )?discoth[èe]que|discoth[èe]que (?:exploit|en activit)",
    "culte": r"lieux? de culte|salles? de pri[èe]re|anciennes? [ée]glises?",
    "conférence": r"amphith[ée][âa]tre de \d+|salles? polyvalentes?",
    "restaurant": r"restaurant[^.]{0,80}\d+\s*couverts|\d+\s*couverts[^.]{0,80}restaurant",
}
# Phrases à ignorer : arrêts de transport, noms de rue ou de quartier, restauration d'entreprise.
IGNORER = re.compile(r"situation/transports|\b(?:bus|m[ée]tro|rer|tram|gare|arr[êe]t|station|ligne)\b|inter-entreprise|\bRIE\b|"
                     r"restaurant d'entreprise|proximit[ée] de l'[ée]glise", re.I)
# Marqueurs d'une phrase seulement hypothétique : l'usage n'est pas celui du bien aujourd'hui.
HYPOTHESE = re.compile(
    r"possibilit[ée]|possibles?\b|peut\b|peuvent|pouvant|id[ée]al\b|id[ée]ale|convient|adapt[ée]|potentiel|"
    r"permet(?:tant)?\b|envisag|susceptible|reconvert|sur demande|ou encore|toutes activit[ée]s|parfait|"
    r"erpable|ou autre|projet|opportunit[ée] pour|vocation|\btype\b", re.I)
# Exclusions : ce que le radar n'accepte pas.
FONDS_SEUL = re.compile(r"cession (?:du )?(?:fonds|droit au bail)|vente (?:du )?fonds|fonds de commerce (?:seul|uniquement)|"
                        r"droit au bail", re.I)
NON_LOCAL = re.compile(r"terrain (?:nu|constructible)|parcelle de terrain|appartement|logement|studio\b|"
                       r"\bmaison\b|pavillon|chambre", re.I)
ERP_DECLARE = re.compile(
    r"(?:class[ée]e?|conforme(?:s)?|aux normes|norme|certification|cat[ée]gorie|accessible|acc[èe]s|adapt[ée]s?)\s*(?:\w+\s+){0,3}ERP\b"
    r"|\bERP\s*(?:de\s+)?(?:cat[ée]gorie|type|PMR|[1-5]\b|conforme|class)|\bERP\b\s*:\s*cat",
    re.I)
ERP_NON_DECLARE = re.compile(r"ERP sur demande|possibilit[ée] de normes|erpable|cat[ée]gorie non d[ée]finie|non class[ée]", re.I)
TYPE_LIBELLE = {"vente-commerces": "Local commercial", "vente-entrepots": "Local d'activités", "vente-bureaux": "Bureaux"}


def sans_accents(texte):
    texte = unicodedata.normalize("NFD", (texte or "").lower())
    return "".join(c for c in texte if not unicodedata.combining(c))


def slug(texte):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", sans_accents(texte))).strip("-")


def phrases(texte):
    """Découpe en phrases ; les puces « - » et les retours à la ligne séparent aussi."""
    return [p.strip() for p in re.split(r"(?<=[.!?;])\s+|\s+-\s+|\n+", texte or "") if p.strip()]


def usages_decrits(c):
    """Renvoie ({usage: [phrases descriptives]}, {usage: [phrases hypothétiques]})."""
    fermes, hypotheses = {}, {}
    titre = c.get("titre") or ""
    for ph in [titre] + phrases(c.get("description")):
        for usage, motif in USAGES.items():
            if not IGNORER.search(ph) and re.search(motif, ph, re.I):
                cible = hypotheses if (HYPOTHESE.search(ph) and ph is not titre) else fermes
                cible.setdefault(usage, []).append(ph[:220])
    return fermes, hypotheses


def proches(a, b):
    """Même bien probable : même département, surface à ±3 %, prix à ±3 % (ou inconnu) et même commune."""
    if a.get("dept") != b.get("dept") or not a.get("surface") or not b.get("surface"):
        return False
    if abs(a["surface"] - b["surface"]) > ECART_DOUBLON * max(a["surface"], b["surface"]):
        return False
    if a.get("prix") and b.get("prix"):
        if abs(a["prix"] - b["prix"]) / max(a["prix"], b["prix"]) > ECART_DOUBLON:
            return False
    return slug(a.get("ville")) == slug(b.get("ville"))


def numero_url(url):
    m = re.search(r"--(\d+)/?$", url or "")
    return m.group(1) if m else None


def evaluer(c, existantes, deja_ajoutees):
    """Renvoie ('ajout', infos) | ('ambigue', motifs) | ('rejet', motif)."""
    url = c.get("url") or ""
    corps = f"{c.get('titre') or ''} {c.get('description') or ''}"

    # Critères durs : si l'un échoue, la candidate est hors périmètre (pas de diagnostic individuel).
    if c.get("connue"):
        return "rejet", "déjà sur le radar"
    if c.get("dept") not in DEPTS:
        return "rejet", "hors des 8 départements"
    if not isinstance(c.get("surface"), int) or c["surface"] < SURFACE_MIN:
        return "rejet", f"surface inférieure à {SURFACE_MIN} m² ou inconnue"
    if c.get("prix") is not None and c["prix"] > PRIX_MAX:
        return "rejet", "prix supérieur à 6 M€"
    if NON_LOCAL.search(corps):
        return "rejet", "logement ou terrain"

    fermes, hypotheses = usages_decrits(c)
    if not fermes and not hypotheses:
        return "rejet", "aucun indice d'usage de salle dans l'annonce"

    # À partir d'ici, il existe au moins un indice d'usage : tout refus est consigné pour diagnostic.
    motifs = []
    if not fermes:
        motifs.append("usage de salle seulement hypothétique (« possibilité », « idéal pour »…)")
    if c.get("prix") is None:
        motifs.append("prix sur demande ou absent")
    for champ, libelle in (("ville", "commune"), ("agence", "agence")):
        if not (c.get(champ) or "").strip():
            motifs.append(f"{libelle} manquante")
    if not url.startswith("https://") or not numero_url(url):
        motifs.append("lien absent ou inexploitable")
    if re.search(r"\bVEFA\b|futur d'ach[èe]vement|brut de b[ée]ton|livraison pr[ée]visionnelle|sur plan", corps, re.I):
        motifs.append("bien non livré (VEFA, brut de béton ou livraison future)")
    if c.get("type") == "vente-bureaux":
        motifs.append("annonce classée « bureaux » : salle probablement partagée de l'immeuble")
    if c.get("prix") and not 300 <= c["prix"] / c["surface"] <= 15000:
        motifs.append(f"prix au m² incohérent ({c['prix'] // c['surface']} €/m²)")
    if c.get("type") not in TYPE_LIBELLE:
        motifs.append(f"type de bien inconnu ({c.get('type')})")
    if re.search(r"\b[àa] vendre ou [àa] louer\b|\b[àa] louer ou [àa] vendre\b", corps, re.I):
        motifs.append("vente ou location : la vente n'est pas la seule offre")
    if FONDS_SEUL.search(corps) and not re.search(r"\bmurs\b", corps, re.I):
        motifs.append("cession de fonds ou de droit au bail sans les murs")
    if c.get("doublon_possible"):
        motifs.append("doublon possible avec : " + ", ".join(map(str, c["doublon_possible"][:6])))
    if c.get("occupe"):
        motifs.append("vendu occupé (bail en cours) : intérêt à apprécier")

    # Doublons contre le radar actuel et contre les ajouts de cette exécution.
    num = numero_url(url)
    for r in existantes:
        if num and num == numero_url(r.get("url")):
            return "rejet", f"déjà sur le radar ({r['_id']})"
        if proches(c, r):
            motifs.append(f"même bien probable que {r['_id']} (déjà sur le radar)")
            break
    for r in deja_ajoutees:
        if proches(c, r):
            motifs.append(f"même bien probable que {r['_id']} (ajouté dans cette exécution)")
            break

    if motifs:
        return "ambigue", motifs
    return "ajout", {"fermes": fermes}


def classer_erp(c):
    """« ERP » seulement si l'annonce déclare un classement ou une conformité ; sinon « verifier ». Jamais « L »."""
    corps = f"{c.get('titre') or ''} {c.get('description') or ''}"
    extraits = [p[:200] for p in phrases(corps) if re.search(r"\bERP\b|cat[ée]gorie [1-5]|recevant du public", p, re.I)]
    declare = [p for p in extraits if ERP_DECLARE.search(p) and not ERP_NON_DECLARE.search(p)]
    if declare:
        return "ERP", "Annonce : « " + " / ".join(declare[:2]) + " » (type et catégorie non établis par règle)"
    if extraits:
        return "verifier", "Annonce : « " + " / ".join(extraits[:2]) + " » (pas de classement déclaré)"
    return "verifier", "Classement ERP non précisé par l'annonce"


def classer_parking(c):
    corps = f"{c.get('titre') or ''} {c.get('description') or ''}"
    for ph in phrases(corps):
        if re.search(r"parking|stationnement", ph, re.I):
            if re.search(r"sans parking|pas de parking|aucun parking|parking public|parking [àa] proximit[ée]|parking en voirie", ph, re.I):
                return "proximite" if re.search(r"proximit[ée]|public", ph, re.I) else "non_precise"
            if re.search(r"parking|stationnement|places?|emplacements?", ph, re.I) and re.search(
                    r"privatif|priv[ée]|\d+\s*(?:places?|emplacements?)|sur place|sous-sol|parking de|parking pour", ph, re.I):
                return "sur_place"
    return "non_precise"


def adresse_publiee(c):
    adr = (c.get("adresse") or "").strip()
    # L'adresse des candidates est souvent « code postal + commune » : ce n'est pas une adresse de voie.
    if not adr or re.fullmatch(rf"{re.escape(c.get('cp') or '')}\s+.*", adr) or not re.search(r"\d+.*(rue|avenue|av\.|boulevard|bd|allée|"
                                                                                                r"chemin|route|place|quai|impasse|zone|za|zac|parc)", adr, re.I):
        return ""
    return adr


def identifiant(c, usages, ids):
    usage = slug(next(iter(usages))) if usages else "salle"
    base = f"{slug(c['ville'])}-{usage}-{c['surface']}"
    if base in ids:
        base = f"{base}-{numero_url(c['url'])}"
    return base


def construire(c, infos, date_iso, ts):
    fermes = infos["fermes"]
    usages = list(fermes)
    erp, erp_detail = classer_erp(c)
    prix, surface = c["prix"], c["surface"]
    r = {
        "_id": None,
        "titre": f"{TYPE_LIBELLE[c['type']]} de {surface} m² à {c['ville'].strip()} (usage décrit : {', '.join(usages)})",
        "ville": c["ville"].strip(),
        "adresse": adresse_publiee(c),
        "dept": c["dept"],
        "agence": c["agence"].strip(),
        "url": c["url"],
        "prix": prix,
        "surface": surface,
        "erp": erp,
        "erpDetail": erp_detail,
        "parking": classer_parking(c),
        "transports": [],
        "statut": "en_vente",
        "notes": (
            f"Ajout automatique par règles, sans relecture humaine, depuis l'annonce BureauxLocaux n° {numero_url(c['url'])}. "
            f"L'annonce décrit : {'; '.join(p.strip(' .,;') for u in usages for p in fermes[u][:1])[:300]}. "
            f"Prix de {format(prix // surface, ',').replace(',', ' ')} €/m². "
            "Classement ERP, capacité, accessibilité, PLU, adresse et desserte non vérifiés : à contrôler avant toute démarche."),
        "nouveau": True,
        "ajoute": ts,
        "vu": date_iso,
    }
    if c.get("occupe"):
        r["occupe"] = True
    return r, usages


def retirer_nouveau_anciens(rows, date_iso):
    jour = datetime.date.fromisoformat(date_iso)
    retires = []
    for r in rows:
        if r.get("nouveau") and r.get("vu") and r["vu"] != date_iso:
            try:
                if (jour - datetime.date.fromisoformat(r["vu"])).days > 7:
                    del r["nouveau"]
                    retires.append(r["_id"])
            except ValueError:
                pass
    return retires


def executer(candidats, payload, examinees, date_iso, max_ajouts, ts):
    """Cœur testable : renvoie (nouveau_payload, examinees, diagnostic). N'écrit rien."""
    rows = payload["rows"]
    ids = {r["_id"] for r in rows}
    nouvelles, ambigues, rejets = [], [], {}
    ordre = sorted((c for c in candidats if not c.get("examinee")), key=lambda c: -c.get("score", 0))
    reportees = 0
    for c in ordre:
        verdict, infos = evaluer(c, rows + nouvelles, nouvelles)
        if verdict == "rejet":
            rejets[infos] = rejets.get(infos, 0) + 1
        elif verdict == "ambigue":
            ambigues.append({"numero": numero_url(c.get("url")), "url": c.get("url"), "ville": c.get("ville"),
                             "dept": c.get("dept"), "surface": c.get("surface"), "prix": c.get("prix"),
                             "agence": c.get("agence"), "motifs": infos})
        elif len(nouvelles) >= max_ajouts:
            reportees += 1
        else:
            r, usages = construire(c, infos, date_iso, ts)
            r["_id"] = identifiant(c, usages, ids | {n["_id"] for n in nouvelles})
            nouvelles.append(r)
            examinees[numero_url(c["url"]) or c["numero"]] = {
                "date": date_iso, "decision": "retenue",
                "motif": "ajout automatique par règles (usage de salle décrit par l'annonce)", "_id": r["_id"]}
    retires = retirer_nouveau_anciens(rows, date_iso)
    sortie = {"date": payload["date"], "rows": rows + nouvelles}
    if nouvelles:
        jj, mm, aaaa = date_iso.split("-")[2], date_iso.split("-")[1], date_iso.split("-")[0]
        sortie["date"] = f"{jj}/{mm}/{aaaa}"
    diag = {"date": date_iso, "candidates_lues": len(candidats), "ajoutees": [n["_id"] for n in nouvelles],
            "reportees_plafond": reportees, "etiquette_nouveau_retiree": retires, "rejets_par_motif": rejets,
            "ambigues_non_publiees": ambigues[:200], "ambigues_total": len(ambigues)}
    return sortie, examinees, diag


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--candidats", default=str(CANDIDATS))
    p.add_argument("--max-ajouts", type=int, default=10)
    p.add_argument("--date", default=datetime.date.today().isoformat())
    p.add_argument("--simulation", action="store_true", help="n'écrit aucun fichier")
    args = p.parse_args()

    try:
        brut = json.loads(open(args.candidats, encoding="utf-8").read())
        candidats = brut["candidats"] if isinstance(brut, dict) else brut
    except (OSError, ValueError, KeyError) as e:
        print(f"ERREUR candidates illisibles ({args.candidats}) : {e}")
        return 1
    if not candidats:
        print("ERREUR liste de candidates vide : la collecte a probablement échoué")
        return 1
    if isinstance(brut, dict) and brut.get("erreurs"):
        print(f"ALERTE la collecte signale {len(brut['erreurs'])} erreur(s) : {brut['erreurs'][:3]}")

    payload = lire_annonces()
    avant = {r["_id"]: json.dumps(r, sort_keys=True) for r in payload["rows"]}
    examinees = json.loads(EXAMINEES.read_text(encoding="utf-8")) if EXAMINEES.exists() else {}
    sortie, examinees, diag = executer(candidats, payload, examinees, args.date, args.max_ajouts, int(time.time() * 1000))

    # Garde-fou : toutes les annonces existantes sont présentes et identiques (hors étiquette « nouveau »).
    for r in sortie["rows"]:
        if r["_id"] in avant:
            ancien = json.loads(avant[r["_id"]])
            ancien.pop("nouveau", None)
            actuel = dict(r)
            actuel.pop("nouveau", None)
            if ancien != actuel:
                print(f"ERREUR l'annonce existante {r['_id']} a été modifiée : abandon")
                return 1
    manquantes = set(avant) - {r["_id"] for r in sortie["rows"]}
    if manquantes:
        print(f"ERREUR annonces existantes disparues : {sorted(manquantes)} : abandon")
        return 1

    print(f"{diag['candidates_lues']} candidates lues : {len(diag['ajoutees'])} ajoutée(s), "
          f"{diag['ambigues_total']} ambiguë(s) non publiée(s), {sum(diag['rejets_par_motif'].values())} hors périmètre, "
          f"{diag['reportees_plafond']} reportée(s) (plafond)")
    for i in diag["ajoutees"]:
        print("  + ", i)
    if args.simulation:
        print("Simulation : aucun fichier écrit.")
        return 0
    DIAGNOSTIC.write_text(json.dumps(diag, ensure_ascii=False, indent=1), encoding="utf-8")
    if diag["ajoutees"] or diag["etiquette_nouveau_retiree"]:
        ecrire_annonces(sortie)
        EXAMINEES.write_text(json.dumps(examinees, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
