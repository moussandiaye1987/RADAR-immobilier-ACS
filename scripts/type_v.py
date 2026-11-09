"""Classification « Radar ERP Type V — lieux de culte » : règles partagées par la veille et la migration.

Aucune IA, aucun réseau : uniquement des règles écrites sur le texte de l'annonce (titre + description).

Deux informations distinctes sont produites pour chaque bien :

1. `erp` — statut affiché par le site (trois valeurs seulement) :
   - « V »        Type V confirmé : une phrase de l'annonce écrit explicitement « type V » (ERP de culte) sans
                  réserve. La phrase est citée mot pour mot dans `erpSource`. Jamais sur une supposition.
   - « L »        Salle Type L existante : l'annonce écrit explicitement « type L », ou décrit une salle recevant du
                  public déjà aménagée (salle de réception, des fêtes, de spectacle…) sans en faire une simple
                  possibilité. Citation dans `erpSource`. Une salle L est convertible en lieu de culte (type V).
   - « verifier » Potentiel Type V — à vérifier : tout le reste. C'est la valeur par défaut, y compris pour un lieu
                  de culte décrit par l'annonce : sans écrit sur le type V, le classement n'est pas confirmé.

2. `profil` — nature du bien pour un projet cultuel (filtre « Profil du bien ») :
   - « culte »        lieu de culte existant ou ancien bâtiment religieux (église, chapelle, temple, mosquée, salle de
                      prière, couvent, presbytère…) ;
   - « associatif »   salle des fêtes, salle polyvalente, local ou salle associative ;
   - « salle »        autre salle recevant du public (réception, spectacle, conférence, séminaire, restaurant) ;
   - « transformable » local sans usage de salle aujourd'hui, à transformer (activité, commerce, entrepôt…).
"""
import re

# --- Découpage ---------------------------------------------------------------------------------------------------

def phrases(texte):
    """Découpe en phrases ; les puces « - », les retours à la ligne et les « <br> » séparent aussi."""
    texte = re.sub(r"<br\s*/?>", "\n", texte or "", flags=re.I)
    return [p.strip() for p in re.split(r"(?<=[.!?;])\s+|\s+-\s+|\n+|\s•\s", texte) if p.strip()]


# --- Indices d'usage ---------------------------------------------------------------------------------------------

# Lieu de culte existant ou ancien bâtiment religieux.
CULTE = re.compile(
    r"lieux? de culte|\bcultuel(?:le)?s?\b|\bculte\b|salles? de pri[èe]re|\bmosqu[ée]es?\b|\bsynagogues?\b|"
    r"[ée]glises?\b|\bchapelles?\b|\btemples?\b|\bparoiss|\bpresbyt[èe]re|\bcouvents?\b|\bmonast[èe]re|\boratoire|"
    r"\bzaou[iï]a|\bzawiya|centre islamique|\bassociations? (?:cultuelle|religieuse|[ée]vang[ée]lique|confessionnelle)|"
    r"communaut[ée] religieuse|congr[ée]gation|\b[ée]difice religieux|\bb[âa]timent religieux", re.I)
# Noms propres et repères géographiques qui contiennent ces mots sans désigner le bien.
CULTE_IGNORER = re.compile(
    r"savigny[- ]le[- ]temple|\bdu\s+temple\b|/\s*temple\b|\btemple\s*/|\bfilles[- ]du[- ]calvaire|"
    r"\bla[- ]chapelle\b|chapelle[- ](?:en|la|sur|aux|saint|gauthier|iger|rablais)\b|"
    r"(?:rue|place|avenue|square|quartier|parvis|proximit[ée]|face|pr[eè]s|derri[eè]re|[àa] c[ôo]t[ée]|"
    r"pied|clocher|centre)\s+(?:de\s+l['’]\s?|du\s+|des\s+|de\s+la\s+)?(?:[ée]glise|chapelle|temple|mosqu[ée]e)|"
    r"[ée]glise[- ](?:de[- ]pantin|saint|notre)", re.I)
# Associations qui ne sont pas des occupants (copropriété de parc d'activités, syndicat).
ASSOCIATIF_IGNORER = re.compile(r"association syndicale|\bASL\b|associations? de copropri|association fonci[èe]re", re.I)
# Salle des fêtes, polyvalente, associative : profil « associatif ».
ASSOCIATIF = re.compile(
    r"salles? des f[êe]tes|salles? polyvalentes?|salles? associatives?|locaux? associatifs?|"
    r"\bassociations?\b|maison des associations|foyer (?:rural|communal)|salles? communales?|salles? paroissiales?", re.I)
# Salle recevant du public : profil « salle ».
SALLE = re.compile(
    r"salles? de r[ée]ception|lieux? de r[ée]ception|salles? de banquet|salles? de spectacles?|salles? de cin[ée]ma|"
    r"anciens? (?:cin[ée]ma|th[ée][âa]tre)|th[ée][âa]tre|discoth[èe]que|salles? de conf[ée]rences?|amphith[ée][âa]tre|"
    r"salles? de s[ée]minaires?|[ée]v[ée]nementiel|restaurant[^.]{0,80}\d+\s*couverts|\d+\s*couverts", re.I)
# Salles relevant du type L (réunions, spectacles, usages multiples).
SALLE_L = re.compile(
    r"salles? (?:de |des )?(?:r[ée]ception|f[êe]tes|banquet|spectacles?|conf[ée]rences?|s[ée]minaires?|cin[ée]ma)|"
    r"salles? polyvalentes?|salles? associatives?|lieux? de r[ée]ception|amphith[ée][âa]tre|\bth[ée][âa]tre\b", re.I)
# Destination d'urbanisme compatible avec un lieu de culte (PLU : équipements d'intérêt collectif).
INTERET_COLLECTIF = re.compile(
    r"int[ée]r[êe]t collectif|\bCINASPIC\b|[ée]quipements? (?:d'int[ée]r[êe]t |collectifs?|publics?|culturels?)|"
    r"accueil du public|recevant du public", re.I)
# Atouts physiques pour accueillir une assemblée.
ATOUTS = re.compile(
    r"plain[- ]pied|rez[- ]de[- ]chauss[ée]e|\bRDC\b|hauteur (?:libre|sous plafond|sous poutre)|\bHSP\b|sans poteaux?|"
    r"b[âa]timent ind[ée]pendant|immeuble ind[ée]pendant|parking|stationnement", re.I)
# Phrases à ignorer : desserte, noms de rue, restauration d'entreprise.
IGNORER = re.compile(r"situation/transports|\b(?:bus|m[ée]tro|rer|tram|gare|arr[êe]t|station|ligne)\b|inter-entreprise|"
                     r"\bRIE\b|restaurant d'entreprise", re.I)
# Marqueurs d'une phrase seulement hypothétique : l'usage n'est pas celui du bien aujourd'hui.
HYPOTHESE = re.compile(
    r"possibilit[ée]|possibles?\b|\bpeut\b(?! accueillir| recevoir)|peuvent(?! accueillir| recevoir)|"
    r"pouvant(?! accueillir| recevoir)|pourrait|id[ée]al\b|id[ée]ale|convient|convenir|adapt[ée]|"
    r"potentiel|permet(?:tant)?\b|envisag|susceptible|reconvert|sur demande|ou encore|toutes activit[ée]s|parfait|"
    r"erpable|ou autre|projet|opportunit[ée] pour|vocation|\btype\b|\btels? que\b|\bdestin[ée]e?s? [àa]\b|"
    r"\bexemples?\b|\bcomme\b", re.I)

# Type écrit explicitement par l'annonce (« ERP de type V », « types L et V », « ERP V »…).
def _type_explicite(lettre):
    return re.compile(rf"\b[Tt]ypes?\s+(?:[A-Z]{{1,2}}\s*(?:,|et|&)\s*)*{lettre}\b|\bERP\s+{lettre}\b|"
                      rf"\bcat[ée]gorie\s+[1-5]\s*,?\s*(?:de\s+)?[Tt]ype\s+{lettre}\b")


V_EXPLICITE = _type_explicite("V")
L_EXPLICITE = _type_explicite("L")


def _reserve(lettre):
    """Réserves qui interdisent de retenir un type : possibilité, projet, obligation, doute, alternative."""
    return re.compile(
        r"possibilit|possibles?\b|transform|am[ée]nag|obten|obligat|sous r[ée]serve|[àa] (?:confirmer|v[ée]rifier|valider|d[ée]finir)|"
        r"\bpeut\b|peuvent|pouvant|projet|[ée]ventuel|\bnon\b|\bpas\b|\bsans\b|sur demande|autoris|changement|"
        r"mise (?:en conformit|aux normes)|erpable|futur|demande|\bsi\b|id[ée]al|potentiel|eventuel|"
        rf"[A-Z]/{lettre}\b|\b{lettre}/[A-Z]\b|type {lettre} ou|ou (?:de )?type {lettre}|\bou\b[^.]{{0,15}}\b{lettre}\b", re.I)


V_RESERVE = _reserve("V")
L_RESERVE = _reserve("L")

PROFILS = {
    "culte": "Lieu de culte ou bâtiment religieux",
    "associatif": "Salle des fêtes, polyvalente ou associative",
    "salle": "Salle recevant du public",
    "transformable": "Local à transformer",
}


# --- Recherche d'indices -----------------------------------------------------------------------------------------

def _hypothetique(ph, motif):
    """L'usage n'est qu'évoqué si un marqueur d'hypothèse précède l'indice dans la phrase (« Idéal pour un lieu de
    culte », « Exemples : salle de réception ») ou figure dans la même proposition. Un marqueur placé après, dans une
    autre proposition, ne compte pas : « Salle de prière de 500 m², ERP sur demande » reste une description."""
    m = motif.search(ph)
    if not m:
        return False
    if HYPOTHESE.search(ph[:m.start()]):
        return True
    suite = re.split(r",|;|:|\s[–—-]\s|\(|\)", ph[m.start():], maxsplit=1)[0]
    return bool(HYPOTHESE.search(suite))


def indices(titre, description):
    """Renvoie {nature: {"fermes": [phrases], "hypotheses": [phrases]}} pour culte / associatif / salle / interet.

    « fermes » : l'annonce décrit le bien tel qu'il est ; « hypotheses » : l'usage n'est évoqué que comme possibilité."""
    sortie = {}
    for ph in ([titre] if titre else []) + phrases(description):
        for nature, motif in (("culte", CULTE), ("associatif", ASSOCIATIF), ("salle", SALLE), ("interet", INTERET_COLLECTIF)):
            if not motif.search(ph):
                continue
            if nature != "interet" and IGNORER.search(ph):
                continue
            # Retirer les noms propres (Savigny-le-Temple, rue du Temple…) puis revérifier qu'il reste un indice cultuel.
            if nature == "culte" and not CULTE.search(CULTE_IGNORER.sub(" ", ph)):
                continue
            if nature == "associatif" and not ASSOCIATIF.search(ASSOCIATIF_IGNORER.sub(" ", ph)):
                continue
            hypothetique = ph is not titre and _hypothetique(ph, motif)
            cible = sortie.setdefault(nature, {"fermes": [], "hypotheses": []})
            cible["hypotheses" if hypothetique else "fermes"].append(ph[:240])
    return sortie


def profil(titre, description):
    """Profil du bien et phrase justificative (ou chaîne vide)."""
    for ph in phrases(f"{titre or ''}. {description or ''}"):
        if V_EXPLICITE.search(ph) and not V_RESERVE.search(ph):
            return "culte", ph[:240]                      # un ERP de type V est, par définition, un lieu de culte
    ind = indices(titre, description)
    for nature in ("culte", "associatif", "salle"):
        if nature in ind and ind[nature]["fermes"]:
            return nature, ind[nature]["fermes"][0]
    for nature in ("culte", "associatif", "salle"):
        if nature in ind and ind[nature]["hypotheses"]:
            # Un usage seulement évoqué (« idéal lieu de culte ») ne change pas la nature du bien.
            return "transformable", ind[nature]["hypotheses"][0]
    return "transformable", ""


def classer_erp(titre, description, url=""):
    """Renvoie (erp, erpDetail, erpSource) selon les règles décrites en tête de module."""
    corps = f"{titre or ''}. {description or ''}"
    for ph in phrases(corps):
        # Le « V » / « L » doit être majuscule dans le texte d'origine : on teste avec la casse conservée.
        if V_EXPLICITE.search(ph) and not V_RESERVE.search(ph):
            citation = ph.strip()[:300]
            return "V", f"Annonce : « {citation} »", f"« {citation} » — {url}".strip(" —")
    for ph in phrases(corps):
        if L_EXPLICITE.search(ph) and not L_RESERVE.search(ph):
            citation = ph.strip()[:300]
            return "L", f"Annonce : « {citation} »", f"« {citation} » — {url}".strip(" —")
    ind = indices(titre, description)
    for nature in ("associatif", "salle"):
        for ph in (ind.get(nature) or {}).get("fermes", []):
            # Une salle de type L : réception, fêtes, spectacle, conférence… (pas un restaurant, type N, ni une
            # discothèque, type P) qui existe aujourd'hui (pas une « ancienne » salle désaffectée).
            if SALLE_L.search(ph) and not re.search(r"\banciens?\b|\banciennes?\b|d[ée]saf+ect|ferm[ée]e? depuis", ph, re.I):
                citation = ph.strip()[:300]
                return ("L", f"Salle existante décrite par l'annonce : « {citation} »",
                        f"« {citation} » — {url}".strip(" —"))
    extraits = [p[:200] for p in phrases(corps) if re.search(r"\bERP\b|cat[ée]gorie [1-5]|recevant du public", p, re.I)]
    if extraits:
        return "verifier", "Type V non confirmé. Annonce : « " + " / ".join(extraits[:2]) + " »", ""
    return "verifier", "Type V non confirmé : l'annonce ne précise pas de classement ERP", ""


def atouts(titre, description):
    """Atouts physiques cités par l'annonce (plain-pied, hauteur, parking…), sans doublon."""
    vus = []
    for m in ATOUTS.finditer(f"{titre or ''} {description or ''}"):
        mot = m.group(0).lower()
        if mot not in vus:
            vus.append(mot)
    return vus


def pertinence(titre, description):
    """Score de priorité pour un projet cultuel : lieu de culte décrit > salle associative > salle > évoqué > atouts."""
    ind = indices(titre, description)
    s = 0
    poids = {"culte": (12, 6), "associatif": (7, 3), "salle": (5, 2), "interet": (4, 4)}
    for nature, (ferme, hypo) in poids.items():
        if nature in ind:
            s += ferme if ind[nature]["fermes"] else 0
            s += hypo if ind[nature]["hypotheses"] else 0
    s += min(3, len(atouts(titre, description)))
    for ph in phrases(f"{titre or ''}. {description or ''}"):
        if V_EXPLICITE.search(ph):
            s += 4 if V_RESERVE.search(ph) else 15        # type V écrit : décisif s'il est affirmé, indice sinon
            break
    return s
