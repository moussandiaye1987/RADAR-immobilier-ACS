"""Types d'ERP (tous types) pour le Radar ERP — Île-de-France.

Chaque annonce porte :
  - typesDeclares   : codes cités explicitement par l'annonce (« ERP type M », « types M et L »)
                      ou activité recevant du public en exploitation (restaurant → N, salle de réception → L…) ;
                      un erp « V » ou « L » justifié (erpSource) vaut type déclaré ;
  - typesPotentiels : codes auxquels le local se prête, sans être déclaré (jamais un type déjà déclaré) ;
  - categorie       : 1 à 5 si l'annonce cite la catégorie ERP (« ERP 5e catégorie »).
Le champ historique `erp` (V / verifier / L) est conservé pour la compatibilité.
"""
import re
import unicodedata

TYPES = {
    "L": "Salles (spectacle, réunion, réception, polyvalente)", "V": "Lieux de culte", "Y": "Musées",
    "M": "Magasins, centres commerciaux", "N": "Restaurants, débits de boissons", "O": "Hôtels, hébergement",
    "P": "Salles de danse et de jeux", "R": "Enseignement, crèches, formation", "S": "Bibliothèques, médiathèques",
    "T": "Salles d'exposition", "U": "Établissements de soins", "W": "Administrations, banques, bureaux",
    "X": "Sport couvert", "J": "Accueil personnes âgées / handicapées",
}
ORDRE = list(TYPES)


def _sans_accents(t):
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()


def _texte(r):
    return " ".join(str(r.get(k) or "") for k in ("titre", "erpDetail", "analyseV", "erpSource"))


TYPE_ECRIT = re.compile(r"\btypes?\s+((?:[LVYMNOPRSTUWXJ](?![A-Za-z])(?:\s*(?:,|&|et|/|-)\s*)?)+)")
CATEGORIE = re.compile(r"(?:ERP|categorie)[^.]{0,25}?\b([1-5])\s*(?:e|eme|er|ere)?\s*(?:cat|categorie)|\b([1-5])\s*(?:e|eme|er|ere)\s*cat", re.I)

POTENTIELS = [
    (r"plain[- ]pied|hauteur|hsp|\d+\s*m\s*sous|entrepot|activite|hangar|atelier|grand volume|batiment independant", "VLX"),
    (r"commerc|boutique|vitrine|magasin|showroom|surface de vente|retail", "M"),
    (r"bureau", "W"),
    (r"restaura|cuisine|brasserie|traiteur", "NL"),
    (r"salle|reception|evenementiel|seminaire|spectacle|conference|polyvalente|salle des fetes", "L"),
    (r"culte|eglise|chapelle|temple|mosquee|priere|synagogue", "V"),
    (r"sport|fitness|padel|escalade|gymnase", "X"),
    (r"creche|ecole|formation|enseignement", "R"),
    (r"medical|sante|cabinet|clinique|soins", "U"),
    (r"hotel|chambres|hebergement", "O"),
    (r"loisirs|bowling|danse|discotheque|jeux", "P"),
]
ACTIVITE = [  # activité recevant du public en exploitation (déclarée)
    (r"restaurant (?:en activite|en exploitation)|murs et fonds.{0,40}restaurant|restaurant.{0,30}murs et fonds", "N"),
    (r"salle de reception (?:en activite|exploitee)|domaine de reception|lieu de reception", "L"),
    (r"creche en activite|micro-?creche en activite", "R"),
    (r"hotel (?:en activite|\d+ chambres)", "O"),
]


def types(r, texte=""):
    """Renvoie (typesDeclares, typesPotentiels, categorie|None) d'après les champs de l'annonce (+ texte brut éventuel)."""
    brut = _texte(r) + " " + (texte or "")
    t = _sans_accents(brut).lower()
    dec = set(r.get("typesDeclares") or [])
    if r.get("erp") in ("V", "L") and r.get("erpSource"):
        dec.add(r["erp"])
    ecrit = _sans_accents(" ".join(str(r.get(k) or "") for k in ("titre", "erpDetail", "erpSource")) + " " + (texte or ""))
    for m in TYPE_ECRIT.finditer(ecrit):
        if re.search(r"possib|potentiel|envisag|instruire|non cit|pas cit|\?", ecrit[max(0, m.start() - 40):m.end() + 12], re.I):
            continue
        dec.update(c for c in re.findall(r"[LVYMNOPRSTUWXJ]", m.group(1)))
    for motif, code in ACTIVITE:
        if re.search(motif, t):
            dec.add(code)
    pot = set(r.get("typesPotentiels") or [])
    for motif, codes in POTENTIELS:
        if re.search(motif, t):
            pot.update(codes)
    if (r.get("profil") or "transformable") in ("culte", "associatif", "salle", "transformable"):
        pot.add("V")  # toutes les fiches historiques du radar sont des candidates « lieu de culte »
    cat = r.get("categorie")
    if not cat:
        m = CATEGORIE.search(_sans_accents(brut))
        cat = int(m.group(1) or m.group(2)) if m else None
    dec_l = [c for c in ORDRE if c in dec]
    pot_l = [c for c in ORDRE if c in pot and c not in dec]
    return dec_l, pot_l, cat


def appliquer(r, texte=""):
    d, p, c = types(r, texte)
    r["typesDeclares"], r["typesPotentiels"] = d, p
    if c:
        r["categorie"] = c
    return r
