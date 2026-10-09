"""Outils partagés par les scripts de veille du Radar ERP Type L."""
import json
import re
import subprocess
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
ANNONCES = RACINE / "annonces.json"
INDEX = RACINE / "index.html"
BALISE_DATA = re.compile(r'(<script id="data" type="application/json">)(.*?)(</script>)', re.S)

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"

# Valeurs reconnues par index.html (constantes DEPTS, MODES, ERP, PARK, STATUT).
DEPTS = ["75", "77", "78", "91", "92", "93", "94", "95"]
MODES = ["Métro", "RER", "Tram", "Transilien", "Bus"]
ERP = ["L", "ERP", "verifier"]
PARKING = ["sur_place", "proximite", "non_precise"]
STATUTS = ["en_vente", "sous_offre", "vendu"]


def lire_annonces(chemin=ANNONCES):
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


def ecrire_annonces(payload):
    """Écrit annonces.json au format du dépôt (indent=1) et synchronise la copie de index.html."""
    ANNONCES.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    compact = json.dumps(payload, ensure_ascii=False)
    if "</" in compact:
        raise ValueError("Les données contiennent « </ », ce qui casserait la balise <script> de index.html")
    html = INDEX.read_text(encoding="utf-8")
    nouveau, n = BALISE_DATA.subn(lambda m: m.group(1) + compact + m.group(3), html, count=1)
    if n != 1:
        raise ValueError("Balise <script id=\"data\"> introuvable dans index.html")
    INDEX.write_text(nouveau, encoding="utf-8")


def donnees_index(html):
    m = BALISE_DATA.search(html)
    return json.loads(m.group(2)) if m else None


def code_index(html):
    """index.html sans la copie des données : sert à vérifier que le code du site n'a pas changé."""
    return BALISE_DATA.sub("", html)


def telecharger(url, timeout=30):
    """Télécharge une page via curl (qui passe par le proxy de l'environnement).

    Renvoie (code_http, url_finale, corps)."""
    sortie = subprocess.run(
        ["curl", "-sSL", "--compressed", "-m", str(timeout), "-A", UA,
         "-H", "Accept-Language: fr-FR,fr;q=0.9", "-o", "-", "-w", "\n__FIN__%{http_code} %{url_effective}", url],
        capture_output=True, text=True, errors="ignore",
    ).stdout
    corps, _, meta = sortie.rpartition("\n__FIN__")
    code, _, finale = meta.partition(" ")
    return int(code or 0), finale, corps
