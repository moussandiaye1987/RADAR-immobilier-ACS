"""Ajoute automatiquement à annonces.json les candidates BureauxLocaux utiles à un lieu de culte (ERP type V).

Usage :
  python3 scripts/ajouter_candidats.py [--candidats veille/.candidats.json] [--max-ajouts 10]
                                       [--max-transformation 3] [--date AAAA-MM-JJ] [--simulation]

Entrée : veille/.candidats.json, produit par scripts/collecter_bureauxlocaux.py.
Sorties (hors --simulation) : annonces.json et la copie de index.html (via commun.ecrire_annonces),
veille/examinees.json (annonces ajoutées) et veille/diagnostic.json (trace des annonces ambiguës).

Principes (aucun appel réseau, aucune IA : uniquement des règles) :
  - une candidate n'est ajoutée que si TOUS les critères « durs » sont remplis (en vente, 8 départements,
    surface ≥ 150 m², prix connu ≤ 6 M€, commune, agence, lien https) ET si elle présente un intérêt pour une
    activité cultuelle. Profils recherchés, par priorité :
      1. culte_existant   lieu de culte existant ou destiné au culte (église, temple, mosquée, salle de prière…) ;
      2. ancien_religieux ancien lieu de culte, ancien bâtiment religieux (chapelle désaffectée, presbytère, couvent…) ;
      3. associatif       local associatif, équipement d'intérêt collectif ;
      4. salle            salle recevant déjà du public (réception, fêtes, polyvalente, spectacle, conférence) ;
      5. transformation   grand local de plain-pied annoncé ERP ou ouvert au public, à transformer
                          (plafonné par --max-transformation pour garder le radar centré sur le culte) ;
    un usage décrit passe avant un usage seulement évoqué comme possibilité ;
  - statut Type V (champ `typeV`, affiché par le site) :
      « V »         Type V confirmé, UNIQUEMENT si une phrase de l'annonce écrit explicitement « type V » sans
                    réserve (citée mot pour mot dans `typeVSource`) ; jamais sur une déduction (« ancienne église »
                    ne suffit pas) ;
      « L »         Salle Type L existante, uniquement si l'annonce écrit explicitement « type L » sans réserve
                    (citée dans `erpSource`, et `erp` = « L ») ;
      « potentiel » Potentiel Type V — à vérifier : tous les autres cas ;
  - une candidate dont les DONNÉES sont ambiguës (doublon possible, cession de fonds, vente ou location, bien non
    livré, bureaux, prix incohérent, donnée manquante) n'est PAS ajoutée : elle est consignée dans veille/diagnostic.json ;
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

from commun import DEPTS, RACINE, V_EXPLICITE, ecrire_annonces, lire_annonces

CANDIDATS = RACINE / "veille" / ".candidats.json"
EXAMINEES = RACINE / "veille" / "examinees.json"
DIAGNOSTIC = RACINE / "veille" / "diagnostic.json"

SURFACE_MIN = 150
SURFACE_TRANSFORMATION = 300
PRIX_MAX = 6_000_000
ECART_DOUBLON = 0.03

LIBELLES = {
    "culte_existant": "lieu de culte",
    "ancien_religieux": "ancien bâtiment religieux",
    "associatif": "local associatif",
    "salle": "salle recevant du public",
    "transformation": "local à transformer",
}
SLUGS = {"culte_existant": "culte", "ancien_religieux": "ancien-culte", "associatif": "associatif",
         "salle": "salle", "transformation": "transformation"}

# Usage décrit par l'annonce : profil -> motif.
CULTE = (r"lieux? de culte|lieux? cultuels?|[ée]difices? (?:cultuels?|religieux)|usage cultuel|activit[ée]s? cultuelles?|"
         r"salles? de pri[èe]res?|\b[ée]glises?\b|\bchapelles?\b|\btemples?\b|\bmosqu[ée]es?\b|\bsynagogues?\b|\boratoires?\b|"
         r"\bpagodes?\b|\bgurdwara|centre (?:cultuel|islamique|bouddhiste)|\bparoiss|associations? (?:cultuelles?|"
         r"[ée]vang[ée]liques?|religieuses?|confessionnelles?)|communaut[ée] religieuse|\bculte\b")
ANCIEN = r"\bancien(?:ne)?s?\b|anciennement|d[ée]saffect|\bex-|autrefois|pr[ée]c[ée]demment"
RELIGIEUX = r"presbyt[èe]re|\bcouvents?\b|monast[èe]re|\babbaye|\bprieur[ée]|\bcure\b|maison paroissiale|congr[ée]gation"
USAGES = {
    "associatif": r"loca(?:l|ux) associatifs?|usage associatif|activit[ée]s? associatives?|salles? associatives?|"
                  r"si[èe]ge (?:d'une |de l')?association|maison des associations|"
                  r"(?:[ée]quipements?|activit[ée]s?) d'int[ée]r[êe]t collectif",
    "salle": r"salles? de r[ée]ception|lieux? de r[ée]ception|salles? des f[êe]tes|salles? de banquet|"
             r"salles? polyvalentes?|salles? de spectacle|salles? de cin[ée]ma|anciens? (?:cin[ée]ma|th[ée][âa]tre)|"
             r"salles? de conf[ée]rence|amphith[ée][âa]tre de \d+|salles? de s[ée]minaire",
}
# Fragments à neutraliser avant la recherche : noms de communes, de rues, d'arrêts ou de repères.
NEUTRES = re.compile(
    r"[\w'’]+(?:-[\w'’]+)*-(?:le|la|les|du|de|des|sur|en)-(?:temple|chapelle|[ée]glise)\b|\b(?:temple|chapelle)-[\w-]+|"
    r"\b[\w'’]+\s+(?:le|la|du)\s+(?:temple|chapelle)\b|"
    r"\b(?:rue|place|avenue|bd|boulevard|all[ée]e|impasse|chemin|quartier|parvis|square|m[ée]tro|station|gare|arr[êe]t)\s+"
    r"(?:de\s+l['’]|du\s+|de\s+la\s+|des\s+)?[\w-]*\s*(?:[ée]glise|temple|chapelle|mosqu[ée]e|synagogue|abbaye|couvent)[\w-]*|"
    r"(?:face|pr[èe]s|proche|proximit[ée]|c[ôo]t[ée]|deux pas|derri[èe]re|devant|voisin(?:e|age)?)\s+"
    r"(?:[àa]\s+|de\s+|d['’]\s*|du\s+|des\s+)?(?:l['’]\s*|la\s+|le\s+|une?\s+)?"
    r"(?:[ée]glise|temple|chapelle|mosqu[ée]e|synagogue|abbaye|couvent)s?\b|clocher|cath[ée]drale de",
    re.I)
# Phrases à ignorer entièrement : transports et restauration d'entreprise.
IGNORER = re.compile(r"situation/transports|inter-entreprise|\bRIE\b|restaurant d'entreprise", re.I)
# Marqueurs d'une phrase seulement hypothétique : l'usage n'est pas celui du bien aujourd'hui.
HYPOTHESE = re.compile(
    r"possibilit[ée]|possibles?\b|peut\b|peuvent|pouvant|id[ée]al\b|id[ée]ale|convient|adapt[ée]|potentiel|"
    r"permet(?:tant)?\b|envisag|susceptible|reconvert|sur demande|ou encore|toutes activit[ée]s|parfait|"
    r"erpable|ou autre|projet|opportunit[ée] pour|vocation|\btype\b|pour (?:une?|des) ", re.I)
# Grand local ouvert au public, à transformer : indice ERP et plain-pied.
PUBLIC = re.compile(r"\bERP\b|recevant du public|accueil du public|accueillir du public|toutes activit[ée]s", re.I)
PLAIN_PIED = re.compile(r"plain[- ]pied|rez[- ]de[- ]chauss[ée]e|\bRDC\b", re.I)
# Exclusions : ce que le radar n'accepte pas.
FONDS_SEUL = re.compile(r"cession (?:du )?(?:fonds|droit au bail)|vente (?:du )?fonds|fonds de commerce (?:seul|uniquement)|"
                        r"droit au bail", re.I)
NON_LOCAL = re.compile(r"terrain (?:nu|constructible)|parcelle de terrain|appartement|logement|studio\b|"
                       r"\bmaison\b(?! (?:des associations|paroissiale))|pavillon|chambre", re.I)
# Type L écrit explicitement par l'annonce (« ERP de type L », « types M et L », « usage type L »…).
L_EXPLICITE = re.compile(r"\b[Tt]ypes?\s+(?:[A-Z]{1,2}\s*(?:,|et)\s*)*L\b|\bERP\s+L\b|\bcat[ée]gorie\s+[1-5]\s*,?\s*(?:de\s+)?[Tt]ype\s+L\b")


def reserve(lettre):
    """Réserves qui interdisent de retenir un type : possibilité, projet, obligation, doute, alternative."""
    return re.compile(
        r"possibilit|possibles?\b|transform|am[ée]nag|obten|obligat|sous r[ée]serve|[àa] (?:confirmer|v[ée]rifier|valider|d[ée]finir)|"
        r"\bpeut\b|peuvent|pouvant|projet|[ée]ventuel|\bnon\b|\bpas\b|\bsans\b|sur demande|autoris|changement|mise (?:en conformit|aux normes)|"
        r"erpable|futur|demande|\bsi\b|id[ée]al|potentiel|eventuel|probabl|vraisemblabl|semble|sans doute|a priori|suppos|"
        rf"[A-Z]/{lettre}\b|\b{lettre}/[A-Z]\b|type {lettre} ou|ou (?:de )?type {lettre}|\bou\b[^.]{{0,15}}\b{lettre}\b", re.I)


V_RESERVE, L_RESERVE = reserve("V"), reserve("L")
TYPE_LIBELLE = {"vente-commerces": "Local commercial", "vente-entrepots": "Local d'activités", "vente-bureaux": "Bureaux"}


def sans_accents(texte):
    texte = unicodedata.normalize("NFD", (texte or "").lower())
    return "".join(c for c in texte if not unicodedata.combining(c))


def slug(texte):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", sans_accents(texte))).strip("-")


def phrases(texte):
    """Découpe en phrases ; les puces « - » et les retours à la ligne séparent aussi."""
    return [p.strip() for p in re.split(r"(?<=[.!?;])\s+|\s+-\s+|\n+", texte or "") if p.strip()]


def profils_decrits(c):
    """Renvoie ({profil: [phrases descriptives]}, {profil: [phrases hypothétiques]}).

    Le titre compte comme description ferme. Les noms de communes (Savigny-le-Temple), de rues (rue de l'Église)
    et les repères (« face à l'église ») sont neutralisés avant la recherche."""
    fermes, hypotheses = {}, {}
    titre = c.get("titre") or ""
    for ph in [titre] + phrases(c.get("description")):
        if IGNORER.search(ph):
            continue
        net = NEUTRES.sub(" ", ph)
        trouves = []
        if re.search(CULTE, net, re.I):
            trouves.append("ancien_religieux" if re.search(ANCIEN, net, re.I) else "culte_existant")
        if re.search(RELIGIEUX, net, re.I):
            trouves.append("ancien_religieux")
        trouves += [p for p, motif in USAGES.items() if re.search(motif, net, re.I)]
        for profil in dict.fromkeys(trouves):
            cible = hypotheses if (HYPOTHESE.search(ph) and ph is not titre) else fermes
            cible.setdefault(profil, []).append(ph[:220])
    return fermes, hypotheses


def transformable(c):
    """Grand local commercial ou d'activités de plain-pied, annoncé ERP ou ouvert au public."""
    corps = f"{c.get('titre') or ''} {c.get('description') or ''}"
    return (c.get("type") in ("vente-commerces", "vente-entrepots") and (c.get("surface") or 0) >= SURFACE_TRANSFORMATION
            and bool(PUBLIC.search(corps)) and bool(PLAIN_PIED.search(corps)))


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


def priorite(infos):
    """Rang d'examen : plus petit = plus prioritaire (profil, puis usage décrit avant usage évoqué)."""
    rang = list(LIBELLES).index(infos["profil"])
    return rang * 2 + (1 if infos["niveau"] == "évoqué" else 0)


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

    fermes, hypotheses = profils_decrits(c)
    statut = classer_type(c)[0]
    if fermes or statut in ("V", "L"):
        profil = next((p for p in LIBELLES if p in fermes), "salle" if statut == "L" else "culte_existant")
        infos = {"profil": profil, "niveau": "décrit", "preuves": fermes}
    elif hypotheses:
        profil = next(p for p in LIBELLES if p in hypotheses)
        infos = {"profil": profil, "niveau": "évoqué", "preuves": hypotheses}
    elif transformable(c):
        infos = {"profil": "transformation", "niveau": "évoqué", "preuves": {}}
    else:
        return "rejet", "aucun indice d'usage cultuel, associatif ou de salle, ni de grand local ouvert au public"

    # À partir d'ici, il existe au moins un indice d'intérêt : tout refus est consigné pour diagnostic.
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
        motifs.append("annonce classée « bureaux » : salle probablement partagée de l'immeuble ou en étage")
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
    return "ajout", infos


def citation_explicite(c, motif, reserve_):
    corps = f"{c.get('titre') or ''}. {c.get('description') or ''}"
    for ph in phrases(corps):
        # La lettre doit être majuscule dans le texte d'origine : on teste donc avec la casse conservée.
        if motif.search(ph) and not reserve_.search(ph):
            return ph.strip()[:300]
    return None


def classer_type(c):
    """Renvoie (typeV, erp, erpDetail, source).

    « V » seulement si une phrase écrit explicitement le type V sans réserve ; « L » seulement si une phrase écrit
    explicitement le type L sans réserve ; sinon « potentiel » (affiché « Potentiel Type V — à vérifier »)."""
    corps = f"{c.get('titre') or ''}. {c.get('description') or ''}"
    v = citation_explicite(c, V_EXPLICITE, V_RESERVE)
    if v:
        return "V", "verifier", f"Annonce : « {v} »", f"« {v} » — {c.get('url')}"
    lc = citation_explicite(c, L_EXPLICITE, L_RESERVE)
    if lc:
        return "L", "L", f"Annonce : « {lc} »", f"« {lc} » — {c.get('url')}"
    extraits = [p[:200] for p in phrases(corps) if re.search(r"\bERP\b|cat[ée]gorie [1-5]|recevant du public", p, re.I)]
    if extraits:
        return "potentiel", "verifier", "Type V non confirmé. Annonce : « " + " / ".join(extraits[:2]) + " »", ""
    return "potentiel", "verifier", "Type V non confirmé : l'annonce ne précise pas de classement ERP", ""


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


def identifiant(c, profil, ids):
    base = f"{slug(c['ville'])}-{SLUGS[profil]}-{c['surface']}"
    if base in ids:
        base = f"{base}-{numero_url(c['url'])}"
    return base


def construire(c, infos, date_iso, ts):
    """Fiche prête à publier, statut « potentiel » (« Potentiel Type V — à vérifier ») sauf type V ou L explicite."""
    profil, evoque = infos["profil"], infos["niveau"] == "évoqué"
    type_v, erp, erp_detail, source = classer_type(c)
    prix, surface = c["prix"], c["surface"]
    preuves = infos["preuves"]
    preuve = "; ".join(p.strip(" .,;") for u in preuves for p in preuves[u][:1])[:300]
    if profil == "transformation":
        constat = ("Grand local de plain-pied annoncé ERP ou ouvert au public, sans usage cultuel cité : "
                   "potentiel de transformation à étudier. ")
    elif preuve:
        constat = f"L'annonce {'évoque seulement comme possibilité' if evoque else 'décrit'} : {preuve}. "
    else:
        constat = ""
    if type_v == "V":
        statut_txt = ("Type V écrit dans l'annonce (voir la source) mais jamais contrôlé : demander le dernier procès-verbal "
                      "de la commission de sécurité ; capacité, accessibilité, PLU, adresse et desserte non vérifiés.")
    elif type_v == "L":
        statut_txt = ("Salle Type L existante (type L écrit dans l'annonce) : un usage cultuel régulier relève du type V et "
                      "suppose une autorisation de travaux ERP et l'avis de la commission de sécurité ; PLU et voisinage à vérifier.")
    else:
        statut_txt = ("Potentiel Type V — à vérifier : aucun classement type V n'est justifié. Pour un lieu de culte, "
                      "vérifier le PLU (changement de destination), l'autorisation ERP, la capacité, l'accessibilité, "
                      "le stationnement et le voisinage.")
    r = {
        "_id": None,
        "titre": f"{TYPE_LIBELLE[c['type']]} de {surface} m² à {c['ville'].strip()} "
                 f"({LIBELLES[profil]}{' évoqué' if evoque and profil != 'transformation' else ''})",
        "ville": c["ville"].strip(),
        "adresse": adresse_publiee(c),
        "dept": c["dept"],
        "agence": c["agence"].strip(),
        "url": c["url"],
        "prix": prix,
        "surface": surface,
        "erp": erp,
        "erpDetail": erp_detail,
        "typeV": type_v,
        "profil": profil,
        "parking": classer_parking(c),
        "transports": [],
        "statut": "en_vente",
        "notes": (
            f"Ajout automatique par règles, sans relecture humaine, depuis l'annonce BureauxLocaux n° {numero_url(c['url'])}. "
            + constat + f"Prix de {format(prix // surface, ',').replace(',', ' ')} €/m². " + statut_txt),
        "nouveau": True,
        "ajoute": ts,
        "vu": date_iso,
    }
    if type_v == "V":
        r["typeVSource"] = source
    if type_v == "L":
        r["erpSource"] = source
    if c.get("occupe"):
        r["occupe"] = True
    return r


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


def executer(candidats, payload, examinees, date_iso, max_ajouts, ts, max_transformation=3):
    """Cœur testable : renvoie (nouveau_payload, examinees, diagnostic). N'écrit rien."""
    rows = payload["rows"]
    ids = {r["_id"] for r in rows}
    nouvelles, ambigues, rejets = [], [], {}
    reportees = 0

    def ambigue(c, motifs):
        ambigues.append({"numero": numero_url(c.get("url")), "url": c.get("url"), "ville": c.get("ville"),
                         "dept": c.get("dept"), "surface": c.get("surface"), "prix": c.get("prix"),
                         "agence": c.get("agence"), "motifs": motifs})

    # Passe 1 : tri. Passe 2 : ajouts par priorité de profil (culte décrit d'abord), puis score de collecte.
    retenues = []
    for c in (c for c in candidats if not c.get("examinee")):
        verdict, infos = evaluer(c, rows, [])
        if verdict == "rejet":
            rejets[infos] = rejets.get(infos, 0) + 1
        elif verdict == "ambigue":
            ambigue(c, infos)
        else:
            retenues.append((c, infos))
    retenues.sort(key=lambda ci: (priorite(ci[1]), -ci[0].get("score", 0)))
    transformations, preuves = 0, {}
    for c, _ in retenues:
        verdict, infos = evaluer(c, rows + nouvelles, nouvelles)   # doublons avec les ajouts de cette exécution
        if verdict == "ambigue":
            ambigue(c, infos)
            continue
        if verdict != "ajout":
            continue
        trop = infos["profil"] == "transformation" and transformations >= max_transformation
        if len(nouvelles) >= max_ajouts or trop:
            reportees += 1
            continue
        r = construire(c, infos, date_iso, ts)
        r["_id"] = identifiant(c, infos["profil"], ids | {n["_id"] for n in nouvelles})
        nouvelles.append(r)
        transformations += infos["profil"] == "transformation"
        preuves[r["_id"]] = next((p for ps in infos["preuves"].values() for p in ps), "grand local ERP de plain-pied")[:160]
        examinees[numero_url(c["url"]) or c["numero"]] = {
            "date": date_iso, "decision": "retenue",
            "motif": f"ajout automatique par règles (profil {infos['profil']}, usage {infos['niveau']} ; statut : {r['typeV']})",
            "_id": r["_id"]}
    retires = retirer_nouveau_anciens(rows, date_iso)
    sortie = {"date": payload["date"], "rows": rows + nouvelles}
    if nouvelles:
        aaaa, mm, jj = date_iso.split("-")
        sortie["date"] = f"{jj}/{mm}/{aaaa}"
    diag = {"date": date_iso, "perimetre": "ERP type V (lieux de culte)", "candidates_lues": len(candidats),
            "ajoutees": [n["_id"] for n in nouvelles],
            "ajoutees_statut_type_v": {n["_id"]: n["typeV"] for n in nouvelles},
            "ajoutees_profil": {n["_id"]: n["profil"] for n in nouvelles},
            "ajoutees_preuve": preuves,
            "reportees_plafond": reportees, "etiquette_nouveau_retiree": retires, "rejets_par_motif": rejets,
            "ambigues_non_publiees": ambigues[:200], "ambigues_total": len(ambigues)}
    return sortie, examinees, diag


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--candidats", default=str(CANDIDATS))
    p.add_argument("--max-ajouts", type=int, default=10)
    p.add_argument("--max-transformation", type=int, default=3,
                   help="ajouts maximum du profil « local à transformer » par exécution")
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
    sortie, examinees, diag = executer(candidats, payload, examinees, args.date, args.max_ajouts,
                                       int(time.time() * 1000), args.max_transformation)

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
        print("  + ", i, f"[{diag['ajoutees_profil'][i]} · {diag['ajoutees_statut_type_v'][i]}]")
        print("       « " + diag["ajoutees_preuve"][i] + " »")
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
