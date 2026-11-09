"""Migration unique du radar Type L vers le radar Type V (lieux de culte) — 09/11/2026.

Usage : python3 scripts/migrer_type_v.py [--simulation]

Pour chaque annonce existante, sans rien supprimer ni modifier des champs d'origine (titre, prix, surface, erp,
erpDetail, notes, liens… restent intacts) :
  - `typeV` : « L » (Salle Type L existante) si l'annonce était classée « L », sinon « potentiel »
    (Potentiel Type V — à vérifier). Aucune annonce existante ne cite le type V : aucune n'est « V » ;
  - `profil` : culte_existant, ancien_religieux, associatif, salle ou transformation (relecture des fiches) ;
  - `analyseV` : analyse au regard d'un lieu de culte (les `notes` d'origine, écrites pour le Type L, sont conservées) ;
  - `archive` + `archiveMotif` + `archiveDate` : annonces hors du nouveau périmètre (vendues occupées, plateaux en
    étage, rez-de-chaussée trop petit). Elles restent dans annonces.json et s'affichent avec l'option
    « Afficher les annonces archivées » du site.
Le script est idempotent : une annonce qui a déjà un `typeV` n'est pas retouchée.
"""
import argparse
import re
import sys

from commun import ecrire_annonces, lire_annonces

DATE = "2026-11-09"

PROFILS = {
    # Lieu de culte existant ou local destiné au culte
    "noisy-le-grand-lieu-de-culte-571": "culte_existant",
    # Anciens lieux de culte / anciennes occupations cultuelles
    "vitry-ancien-lieu-de-culte-1103": "ancien_religieux",
    "savigny-le-temple-reception-3080": "ancien_religieux",
    # Locaux associatifs ou d'intérêt collectif
    "paris18-montmartre-252": "associatif",
    "chaville-487": "associatif",
    "livry-gargan-cabinet-250": "associatif",
    # Salles recevant déjà du public
    **{i: "salle" for i in (
        "eragny-reception", "montereau-restaurant-reception-400", "rambouillet-reception-950", "versailles-reception-1000",
        "vincennes-consultim", "vincennes-evolis", "villeneuve-le-comte-reception-790", "saint-denis-reception-2076",
        "paris7-ancienne-salle-de-spectacles-430", "champs-sur-marne-amphitheatre-665", "champs-sur-marne-erpable-amphi-665",
        "gometz-la-ville-reception-390", "paris14-general-leclerc-285", "vitry-plateau-lilas", "garges-toulouse-lautrec-690",
        "coubron-ensemble-608", "sartrouville-restaurant-529", "ozoir-la-ferriere-restaurant-657", "trappes-kepler-1344",
        "ezanville-pole-loisirs-3695", "creteil-reception-519", "saint-denis-reception-2192")},
}

ARCHIVES = {
    "eragny-reception": "Vendue occupée avec un bail 3-6-9 signé en mars 2026 : indisponible pour un lieu de culte avant plusieurs années.",
    "gonesse-creche-842": "Vendue occupée par une crèche jusqu'en 2034 : placement locatif, indisponible pour un lieu de culte.",
    "bretigny-commerce-erp-400": "Vendue occupée (bail commercial 3-6-9) : placement locatif, indisponible pour un lieu de culte.",
    "saint-ouen-l-aumone-1040-occupe": "Vendue occupée : investissement locatif, indisponible pour un lieu de culte.",
    "savigny-le-temple-murs-occupes-940": "Murs vendus occupés : indisponibles pour un lieu de culte tant que le bail court.",
    "cergy-petit-albi-576": "Plateau de bureaux au 3e étage : accueil d'une assemblée de fidèles peu plausible (évacuation, copropriété).",
    "noisy-le-grand-fujy-220": "Plateau de bureaux au 1er étage, 220 m² : jauge et évacuation inadaptées à un lieu de culte.",
    "rosny-jules-ferry-255": "Plateau au 2e étage d'un immeuble de bureaux : inadapté à un lieu de culte.",
    "montreuil-rue-de-paris-331": "Plateau de bureaux au 1er étage d'un immeuble tertiaire : inadapté à un lieu de culte.",
    "stouen-michelet": "Plateau de bureaux en étage, non ERP : accueil du public peu plausible.",
    "les-lilas-erp5": "Plateau en R+1 : jauge limitée par les escaliers, peu adapté à une assemblée de fidèles.",
    "pre-saint-gervais-atelier-244": "126 m² seulement en rez-de-chaussée (le reste en sous-sol) : jauge trop faible pour un lieu de culte.",
}

ANALYSES = {
    "noisy-le-grand-lieu-de-culte-571": "Local explicitement destiné à un lieu de culte par l'annonce : le profil le plus direct du radar. "
        "Vendu en VEFA (livraison prévue en février 2027), brut de béton : l'aménagement peut être conçu dès le départ aux "
        "normes du type V (dégagements, effectif, accessibilité). Classement type V non justifié à ce jour : demander la "
        "destination prévue au permis et le règlement de copropriété.",
    "vitry-ancien-lieu-de-culte-1103": "Ancien lieu de culte annoncé ERP, 1 103 m² de plain-pied : l'usage cultuel antérieur est un "
        "argument fort, mais le type V n'est pas cité par l'annonce et l'ancien classement peut être caduc. Demander le dernier "
        "procès-verbal de la commission de sécurité, l'effectif autorisé et la destination d'urbanisme. Hauteur de 3 m.",
    "savigny-le-temple-reception-3080": "L'annonce indique une salle des fêtes à l'étage anciennement occupée par une association "
        "évangélique : usage cultuel antérieur, mais salle en étage (évacuation et jauge à vérifier). 3 080 m² à 584 €/m² : "
        "très grande emprise, prix bas. Classement ERP non précisé.",
    "paris18-montmartre-252": "Destination réservée aux activités d'intérêt collectif : c'est la famille d'urbanisme où se rangent "
        "les lieux de culte, ce qui peut éviter un changement de destination (à confirmer en mairie). Seulement 98 m² en "
        "rez-de-chaussée : petite salle de prière ou local associatif, pas une grande assemblée.",
    "chaville-487": "Ancienne crèche déjà ERP et accessible PMR : profil d'équipement recevant du public, compatible avec un local "
        "associatif ou cultuel. Situé au 1er étage : effectif limité par les escaliers, à faire vérifier.",
    "livry-gargan-cabinet-250": "Ancien cabinet médical de plain-pied, accessible PMR, sur axe commerçant : convient à une petite "
        "salle associative ou de prière après décloisonnement. ERP de type V non justifié ; changement de destination à instruire.",
    "vincennes-consultim": "Salle Type L existante (ERP 5e catégorie, types M et L cités par l'annonce). Un usage cultuel régulier "
        "relève du type V : autorisation de travaux ERP et avis de la commission de sécurité à prévoir. Copropriété à consulter.",
    "vincennes-evolis": "Même bien que l'annonce Consult'Im (Salle Type L existante) proposé par une autre agence ; ERP 5e catégorie "
        "en rez-de-chaussée. Type V non justifié.",
    "rambouillet-reception-950": "Salle Type L existante : salle de réception exploitée avec avis favorable de la commission de "
        "sécurité, grande jauge et grand parking. Probablement une cession de fonds avec bail (loyer annoncé) : vérifier que "
        "les murs sont vendus avant toute démarche. Usage cultuel = type V à instruire.",
    "versailles-reception-1000": "Salle Type L existante : salle de réception de 500 couverts rénovée en 2018. Loyer et bail cités : "
        "très probablement une cession de fonds et non les murs, à vérifier. Usage cultuel = type V à instruire.",
    "montereau-restaurant-reception-400": "Classée « L » dans le radar d'origine, mais l'annonce laisse un doute (N ou L) : demander le "
        "procès-verbal de sécurité. Site isolé avec 200 places de parking, utile pour une assemblée ; très éloigné de Paris.",
    "paris7-ancienne-salle-de-spectacles-430": "Ancienne salle de spectacles de 430 m² de plain-pied avec volume d'origine : "
        "configuration d'assemblée proche d'un lieu de culte, mais classement ERP caduc (fermée depuis 1986) et prix très élevé "
        "(10 465 €/m²).",
}

GABARIT = {
    "culte_existant": "Lieu de culte existant ou destiné au culte selon l'annonce.",
    "ancien_religieux": "Ancien bâtiment religieux ou ancien usage cultuel.",
    "associatif": "Local associatif ou d'intérêt collectif.",
    "salle": "Salle recevant déjà du public : configuration d'assemblée, réutilisable pour un culte après instruction ERP type V.",
    "transformation": "Local à transformer : aucun usage cultuel n'est cité par l'annonce.",
}


def analyse(r, profil):
    if r["_id"] in ANALYSES:
        return ANALYSES[r["_id"]]
    texte = (r.get("erpDetail", "") + " " + r.get("notes", "")).lower()
    morceaux = [GABARIT[profil]]
    if r["erp"] == "L":
        morceaux.append("Salle Type L existante : un usage cultuel régulier relève du type V (autorisation de travaux ERP et "
                        "avis de la commission de sécurité).")
    elif r["erp"] == "ERP":
        morceaux.append("Annoncé ERP sans type précisé : le passage au type V reste à instruire.")
    else:
        morceaux.append("Aucun classement ERP justifié : changement de destination (PLU), autorisation de travaux ERP et "
                        "commission de sécurité à prévoir.")
    if "étage" in texte and "rez" not in texte and "rdc" not in texte:
        morceaux.append("Surface en partie en étage : effectif accueilli limité par les dégagements.")
    if "plain-pied" in texte or "rdc" in texte or "rez-de-chaussée" in texte:
        morceaux.append("Plain-pied ou rez-de-chaussée : atout pour l'accueil et l'évacuation des fidèles.")
    if r.get("parking") == "sur_place":
        morceaux.append("Stationnement sur place, utile lors des offices.")
    copro = ("copropriété" in texte or "logements" in texte) and not re.search(r"(?:pas de|sans|aucune) copropriété", texte)
    if copro:
        morceaux.append("Copropriété ou logements proches : règlement et voisinage à vérifier.")
    if r.get("occupe"):
        morceaux.append("Vendu occupé ou en partie loué : disponibilité à vérifier.")
    return " ".join(morceaux)


def migrer(payload):
    n = {"migrees": 0, "archivees": 0}
    for r in payload["rows"]:
        if "typeV" in r:
            continue
        profil = PROFILS.get(r["_id"], "transformation")
        r["typeV"] = "L" if r["erp"] == "L" else "potentiel"
        r["profil"] = profil
        r["analyseV"] = analyse(r, profil)
        if r["_id"] in ARCHIVES:
            r["archive"] = True
            r["archiveMotif"] = ARCHIVES[r["_id"]]
            r["archiveDate"] = DATE
            n["archivees"] += 1
        n["migrees"] += 1
    return n


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--simulation", action="store_true")
    args = p.parse_args()
    payload = lire_annonces()
    ids = {r["_id"] for r in payload["rows"]}
    inconnus = (set(PROFILS) | set(ARCHIVES) | set(ANALYSES)) - ids
    if inconnus:
        print("ERREUR identifiants inconnus :", sorted(inconnus))
        return 1
    n = migrer(payload)
    print(f"{len(payload['rows'])} annonces : {n['migrees']} migrées, {n['archivees']} archivées (conservées).")
    if not args.simulation:
        ecrire_annonces(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
