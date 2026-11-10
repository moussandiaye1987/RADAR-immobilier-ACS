"""Migration unique du radar vers le type V (lieux de culte) : reclasse les annonces existantes sans en supprimer.

Usage :
  python3 scripts/migrer_type_v.py [--date AAAA-MM-JJ] [--cache fichier.json] [--simulation]

Pour chaque annonce de annonces.json :
  1. relit le texte d'origine de l'annonce (BureauxLocaux : description complète de la page) ; si la page n'est
     plus disponible, seuls le titre et le détail ERP de la fiche servent (jamais nos notes d'analyse) ;
  2. calcule avec scripts/type_v.py le profil du bien (culte, associatif, salle, transformable) et le statut
     (V = Type V confirmé, L = Salle Type L existante, verifier = Potentiel Type V — à vérifier), avec citation ;
  3. archive (sans supprimer) les biens inadaptés à un lieu de culte : vendu occupé, plateau en étage,
     annonce retirée (HTTP 404/410). Une annonce archivée reste dans annonces.json avec son motif ; le site la
     masque par défaut et l'affiche avec la case « Afficher les annonces archivées » ;
  4. écrit chaque décision dans veille/migration_type_v.json (avant/après, motif, citation, source du texte).

Les données d'origine sont conservées : ancien statut dans `migration.erpAvant`, notes d'analyse inchangées.
Idempotent : une annonce déjà migrée (champ `profil` présent) n'est pas retraitée.
"""
import argparse
import datetime
import html
import json
import re
import sys
import time
from pathlib import Path

import type_v as T
from commun import RACINE, ecrire_annonces, lire_annonces, telecharger

DECISIONS = RACINE / "veille" / "migration_type_v.json"
CONTEXTE = re.compile(r'<script type="text/json" id="react-context">(.*?)</script>', re.S)

OCCUPE_DISPONIBLE = re.compile(r"murs et (?:le )?fonds|partiellement occup|un lot de \d+ m² (?:est )?lou", re.I)
EN_ETAGE = re.compile(r"\b\d+(?:er|e|ème)\s+[ée]tage\b|situ[ée] [àa] l'[ée]tage|plateaux? (?:de bureaux|modulable|rénové)|^plateau", re.I)
AU_SOL = re.compile(r"\bRDC\b|rez[- ]de[- ](?:chauss[ée]e|jardin)|plain[- ]pied", re.I)


def texte(s):
    return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<(?!br)[^>]+>", " ", s or ""))).strip()


def relire(url, cache):
    """Description d'origine de l'annonce, ou None si la page n'est plus lisible. Renvoie (description, code, url_finale)."""
    if url in cache:
        return cache[url]["description"], cache[url]["code"], cache[url]["finale"]
    description, code, finale = None, 0, url
    if "bureauxlocaux.com/annonce/" in url:
        code, finale, corps = telecharger(url)
        m = CONTEXTE.search(corps)
        if code == 200 and m and "/annonce/" in finale:
            try:
                description = texte(json.loads(m.group(1))["global"]["listing"]["description"])
            except (KeyError, TypeError, ValueError):
                description = None
        time.sleep(0.6)
    elif url:
        code, finale, _ = telecharger(url)
    cache[url] = {"description": description, "code": code, "finale": finale}
    return description, code, finale


def decision_archive(r, source_texte, code):
    """Motif d'archivage, ou None si l'annonce reste dans le radar actif."""
    if code in (404, 410):
        return f"Annonce retirée par le site (HTTP {code}) lors du contrôle du passage au type V."
    # Les notes d'analyse servent ici de relevé factuel (étage, occupation), jamais de justificatif ERP.
    fiche = f"{r.get('titre', '')} · {r.get('erpDetail', '')} · {r.get('notes', '')} · {source_texte or ''}"
    if r.get("occupe") and not OCCUPE_DISPONIBLE.search(fiche):
        return "Vendu occupé (bail en cours) : le local n'est pas disponible pour y installer un lieu de culte."
    resume = f"{r.get('titre', '')} · {r.get('erpDetail', '')} · {r.get('notes', '')}"
    if EN_ETAGE.search(resume) and not AU_SOL.search(resume):
        return ("Plateau en étage sans rez-de-chaussée : inadapté à l'accueil d'une assemblée de fidèles "
                "(évacuation, accessibilité PMR, copropriété tertiaire).")
    return None


def analyse(prof, citation, erp, atouts_cites, source, interet=""):
    morceaux = []
    libelle = T.PROFILS[prof]
    if citation:
        morceaux.append(f"{libelle} — l'annonce indique : « {citation.strip(' .')} ».")
    else:
        morceaux.append(f"{libelle} : l'annonce ne décrit ni usage cultuel ni salle ; potentiel à évaluer (volume, accès, PLU).")
    if interet and interet != citation:
        morceaux.append(f"Destination ou accueil du public mentionnés : « {interet.strip(' .')} ».")
    if atouts_cites:
        morceaux.append("Atouts cités : " + ", ".join(atouts_cites[:5]) + ".")
    morceaux.append({"V": "Type V confirmé par l'annonce (voir la source).",
                     "L": "Salle de type L existante : conversion en lieu de culte (type V) à instruire.",
                     "verifier": "Type V non confirmé : classement ERP, capacité, accessibilité et PLU "
                                 "(équipement d'intérêt collectif) à vérifier."}[erp])
    if source != "annonce":
        morceaux.append("Texte d'origine de l'annonce indisponible : lecture faite sur la fiche du radar.")
    return " ".join(morceaux)


def migrer(payload, date_iso, cache, relecture=True):
    decisions = {}
    for r in payload["rows"]:
        if "profil" in r:
            continue
        description, code, finale = relire(r["url"], cache) if relecture else (None, 0, r["url"])
        if description:
            titre, corps, source = "", description, "annonce"
        else:
            # Page indisponible : uniquement les éléments factuels de la fiche (pas les notes d'analyse).
            titre, corps, source = r.get("titre", ""), r.get("erpDetail", ""), "fiche"
        prof, citation = T.profil(titre, corps)
        erp, erp_detail, erp_source = T.classer_erp(titre, corps, r["url"])
        if source == "fiche" and erp in ("V", "L") and not re.search(r"Annonce\s*:|«", r.get("erpDetail", "")):
            erp, erp_source = "verifier", ""          # sans le texte de l'annonce, pas de justificatif recevable
        avant = {"erp": r["erp"], "erpDetail": r.get("erpDetail", "")}
        motif_archive = decision_archive(r, description, code)

        r["profil"] = prof
        r["erp"] = erp
        if erp in ("V", "L"):
            r["erpSource"] = erp_source
            r["erpDetail"] = erp_detail
        else:
            r.pop("erpSource", None)
            r["erpDetail"] = re.sub(r"Type L non confirmé", "Type V non confirmé", r.get("erpDetail", "")) or erp_detail
        ind = T.indices(titre, corps).get("interet") or {}
        interet = (ind.get("fermes") or ind.get("hypotheses") or [""])[0]
        r["analyseV"] = analyse(prof, citation, erp, T.atouts(titre, corps), source, interet)
        r["migration"] = {"date": date_iso, "erpAvant": avant["erp"]}
        if motif_archive:
            r["archive"] = {"date": date_iso, "motif": motif_archive}
        decisions[r["_id"]] = {
            "source_texte": source, "http": code, "profil": prof, "citation": citation,
            "erp_avant": avant["erp"], "erp_apres": erp, "erpSource": r.get("erpSource", ""),
            "archive": motif_archive or "", "url": r["url"], "url_finale": finale,
        }
    return payload, decisions


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=datetime.date.today().isoformat())
    p.add_argument("--cache", help="fichier JSON de cache des pages relues (accélère une seconde exécution)")
    p.add_argument("--simulation", action="store_true", help="n'écrit rien, affiche les décisions")
    args = p.parse_args()

    cache = {}
    if args.cache and Path(args.cache).exists():
        cache = json.loads(Path(args.cache).read_text(encoding="utf-8"))
    payload = lire_annonces()
    ids_avant = [r["_id"] for r in payload["rows"]]
    payload, decisions = migrer(payload, args.date, cache)
    if args.cache:
        Path(args.cache).write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    assert [r["_id"] for r in payload["rows"]] == ids_avant, "aucune annonce ne doit disparaître"
    compte = {}
    for d in decisions.values():
        cle = ("archivée" if d["archive"] else d["erp_apres"], d["profil"])
        compte[cle] = compte.get(cle, 0) + 1
    print(f"{len(decisions)} annonces migrées ({sum(d['source_texte'] == 'annonce' for d in decisions.values())} relues sur l'annonce d'origine)")
    for (statut, prof), n in sorted(compte.items()):
        print(f"  {statut:9} {prof:13} {n}")
    if args.simulation:
        for i, d in decisions.items():
            print(f"{i:42} {d['erp_avant']:8}→ {d['erp_apres']:8} {d['profil']:13} {('ARCHIVE ' + d['archive'][:60]) if d['archive'] else ''} | {d['citation'][:90]}")
        return 0
    ecrire_annonces(payload)
    DECISIONS.write_text(json.dumps({"date": args.date, "decisions": decisions}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("annonces.json, index.html et veille/migration_type_v.json écrits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
