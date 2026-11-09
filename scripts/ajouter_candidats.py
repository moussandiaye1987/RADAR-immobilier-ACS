"""Ajoute automatiquement à annonces.json les candidates BureauxLocaux utiles à un projet de lieu de culte (ERP type V).

Usage :
  python3 scripts/ajouter_candidats.py [--candidats veille/.candidats.json] [--max-ajouts 10]
                                       [--date AAAA-MM-JJ] [--simulation]

Entrée : veille/.candidats.json, produit par scripts/collecter_bureauxlocaux.py.
Sorties (hors --simulation) : annonces.json et la copie de index.html (via commun.ecrire_annonces),
veille/examinees.json (annonces ajoutées) et veille/diagnostic.json (trace des annonces ambiguës).

Principes (aucun appel réseau, aucune IA : uniquement les règles de scripts/type_v.py) :
  - une candidate n'est ajoutée que si TOUS les critères « durs » sont remplis (en vente, 8 départements,
    surface ≥ 150 m², prix connu ≤ 6 M€, commune, agence, lien https) ET si l'annonce présente un intérêt pour un
    lieu de culte : lieu de culte ou bâtiment religieux, salle des fêtes / polyvalente / associative, salle recevant du
    public, type V ou L écrit (niveau « décrit ») ; usage seulement évoqué comme possibilité ou destination d'intérêt
    collectif / accueil du public (niveau « évoqué »). Les candidates passent par ordre de pertinence cultuelle
    (lieu de culte d'abord), les niveaux « décrits » avant les « évoqués » ;
  - une candidate dont les DONNÉES sont ambiguës (doublon possible, cession de fonds, vente ou location, bien non
    livré, bureaux, prix incohérent, donnée manquante) n'est PAS ajoutée : elle est consignée dans veille/diagnostic.json ;
  - statut ERP (`erp`) : « verifier » = « Potentiel Type V — à vérifier » par défaut, y compris pour un lieu de culte
    décrit ; « V » (« Type V confirmé ») UNIQUEMENT si une phrase écrit explicitement « type V » sans réserve ;
    « L » (« Salle Type L existante ») si l'annonce écrit « type L » ou décrit une salle existante. La phrase est citée
    mot pour mot dans `erpSource`. Profil (`profil`) et lecture type V (`analyseV`) sont calculés par type_v.py ;
    transports et référence restent vides, le parking n'est renseigné que si l'annonce le cite ;
  - aucune annonce existante n'est modifiée, supprimée, archivée ni passée en « vendu » (seule l'étiquette
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

import type_v as T
from commun import DEPTS, RACINE, ecrire_annonces, lire_annonces

CANDIDATS = RACINE / "veille" / ".candidats.json"
EXAMINEES = RACINE / "veille" / "examinees.json"
DIAGNOSTIC = RACINE / "veille" / "diagnostic.json"

SURFACE_MIN = 150
PRIX_MAX = 6_000_000
ECART_DOUBLON = 0.03

# Exclusions : ce que le radar n'accepte pas.
FONDS_SEUL = re.compile(r"cession (?:du )?(?:fonds|droit au bail)|vente (?:du )?fonds|fonds de commerce (?:seul|uniquement)|"
                        r"droit au bail", re.I)
NON_LOCAL = re.compile(r"terrain (?:nu|constructible)|parcelle de terrain|appartement|logement|studio\b|"
                       r"\bmaison\b|pavillon|chambre", re.I)
TYPE_LIBELLE = {"vente-commerces": "Local commercial", "vente-entrepots": "Local d'activités", "vente-bureaux": "Bureaux"}


def sans_accents(texte):
    texte = unicodedata.normalize("NFD", (texte or "").lower())
    return "".join(c for c in texte if not unicodedata.combining(c))


def slug(texte):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", sans_accents(texte))).strip("-")


def interet(c):
    """Renvoie (niveau, {nature: [phrases]}) : niveau « décrit », « évoqué » ou None (aucun intérêt pour un lieu de culte)."""
    titre, desc = c.get("titre") or "", c.get("description") or ""
    ind = T.indices(titre, desc)
    erp = T.classer_erp(titre, desc)[0]
    fermes = {n: v["fermes"] for n, v in ind.items() if n != "interet" and v["fermes"]}
    if fermes or erp == "V" or (erp == "L" and T.L_EXPLICITE.search(f"{titre} {desc}")):
        return "décrit", fermes or {"type écrit": [T.classer_erp(titre, desc)[1]]}
    evoques = {n: v["hypotheses"] for n, v in ind.items() if n != "interet" and v["hypotheses"]}
    if "interet" in ind:
        evoques["intérêt collectif"] = ind["interet"]["fermes"] + ind["interet"]["hypotheses"]
    if evoques:
        return "évoqué", evoques
    return None, {}


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

    niveau, usages = interet(c)
    if not niveau:
        return "rejet", "aucun indice d'usage cultuel, associatif ou de salle dans l'annonce"

    # À partir d'ici, il existe au moins un indice d'usage : tout refus est consigné pour diagnostic.
    motifs = []
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
    return "ajout", {"usages": usages, "niveau": niveau}


def classer_parking(c):
    corps = f"{c.get('titre') or ''} {c.get('description') or ''}"
    for ph in T.phrases(corps):
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


def identifiant(c, prof, ids):
    usage = {"culte": "culte", "associatif": "salle-associative", "salle": "salle", "transformable": "local"}[prof]
    base = f"{slug(c['ville'])}-{usage}-{c['surface']}"
    if base in ids:
        base = f"{base}-{numero_url(c['url'])}"
    return base


def construire(c, infos, date_iso, ts):
    """Fiche prête à publier. Statut « verifier » (« Potentiel Type V — à vérifier ») sauf type V / salle L justifiés."""
    titre, desc = c.get("titre") or "", c.get("description") or ""
    evoque = infos["niveau"] == "évoqué"
    erp, erp_detail, erp_source = T.classer_erp(titre, desc, c["url"])
    prof, citation = T.profil(titre, desc)
    prix, surface = c["prix"], c["surface"]
    preuve = "; ".join(p.strip(" .,;") for u in infos["usages"] for p in infos["usages"][u][:1])[:300]
    libelle = {"culte": "lieu de culte", "associatif": "salle associative", "salle": "salle", "transformable": "à transformer"}[prof]
    atouts = T.atouts(titre, desc)
    r = {
        "_id": None,
        "titre": f"{TYPE_LIBELLE[c['type']]} de {surface} m² à {c['ville'].strip()} "
                 f"({libelle}{', usage évoqué' if evoque else ''})",
        "ville": c["ville"].strip(),
        "adresse": adresse_publiee(c),
        "dept": c["dept"],
        "agence": c["agence"].strip(),
        "url": c["url"],
        "prix": prix,
        "surface": surface,
        "erp": erp,
        "erpDetail": erp_detail,
        "profil": prof,
        "parking": classer_parking(c),
        "transports": [],
        "statut": "en_vente",
        "analyseV": (
            f"{T.PROFILS[prof]} — l'annonce {'évoque seulement comme possibilité' if evoque else 'indique'} : « {preuve or citation} ». "
            + (f"Atouts cités : {', '.join(atouts[:5])}. " if atouts else "")
            + {"V": "Type V confirmé par l'annonce (voir la source).",
               "L": "Salle de type L existante : conversion en lieu de culte (type V) à instruire.",
               "verifier": "Type V non confirmé : classement ERP, capacité, accessibilité et PLU (équipement d'intérêt "
                           "collectif) à vérifier."}[erp]),
        "notes": (
            f"Ajout automatique par règles, sans relecture humaine, depuis l'annonce BureauxLocaux n° {numero_url(c['url'])}. "
            f"Prix de {format(prix // surface, ',').replace(',', ' ')} €/m². "
            "Capacité, accessibilité, PLU, adresse et desserte non vérifiés."),
        "nouveau": True,
        "ajoute": ts,
        "vu": date_iso,
    }
    if erp in ("V", "L"):
        r["erpSource"] = erp_source
    if c.get("occupe"):
        r["occupe"] = True
    return r, prof


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
    # Ordre de passage : pertinence pour un lieu de culte (lieu de culte décrit d'abord), puis score de collecte.
    ordre = sorted((c for c in candidats if not c.get("examinee")),
                   key=lambda c: (-T.pertinence(c.get("titre"), c.get("description")), -c.get("score", 0)))
    reportees = 0

    def ambigue(c, motifs):
        ambigues.append({"numero": numero_url(c.get("url")), "url": c.get("url"), "ville": c.get("ville"),
                         "dept": c.get("dept"), "surface": c.get("surface"), "prix": c.get("prix"),
                         "agence": c.get("agence"), "motifs": motifs})

    def ajouter(c, infos):
        r, prof = construire(c, infos, date_iso, ts)
        r["_id"] = identifiant(c, prof, ids | {n["_id"] for n in nouvelles})
        nouvelles.append(r)
        examinees[numero_url(c["url"]) or c["numero"]] = {
            "date": date_iso, "decision": "retenue",
            "motif": f"ajout automatique par règles type V (profil {r['profil']}, intérêt {infos['niveau']} ; statut ERP : {r['erp']})",
            "_id": r["_id"]}

    # Passe 1 : intérêt avéré (usage décrit, type V ou L écrit). Passe 2 : usage seulement évoqué.
    evoquees = []
    for c in ordre:
        verdict, infos = evaluer(c, rows + nouvelles, nouvelles)
        if verdict == "rejet":
            rejets[infos] = rejets.get(infos, 0) + 1
        elif verdict == "ambigue":
            ambigue(c, infos)
        elif infos["niveau"] == "évoqué":
            evoquees.append(c)
        elif len(nouvelles) >= max_ajouts:
            reportees += 1
        else:
            ajouter(c, infos)
    for c in evoquees:
        verdict, infos = evaluer(c, rows + nouvelles, nouvelles)
        if verdict == "ambigue":
            ambigue(c, infos)
        elif verdict == "ajout":
            if len(nouvelles) >= max_ajouts:
                reportees += 1
            else:
                ajouter(c, infos)
    retires = retirer_nouveau_anciens(rows, date_iso)
    sortie = {"date": payload["date"], "rows": rows + nouvelles}
    if nouvelles:
        aaaa, mm, jj = date_iso.split("-")
        sortie["date"] = f"{jj}/{mm}/{aaaa}"
    diag = {"date": date_iso, "candidates_lues": len(candidats), "ajoutees": [n["_id"] for n in nouvelles],
            "ajoutees_statut_erp": {n["_id"]: n["erp"] for n in nouvelles},
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
