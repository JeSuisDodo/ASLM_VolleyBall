#!/usr/bin/env python3
"""
Mise à jour des matchs de l'ASLM Volley-Ball.

Lit les calendriers et classements publiés par la FFvolley et écrit le fichier
matchs.json lu par le site. À lancer une fois par jour (voir le fichier
.github/workflows/maj-matchs.yml).

Aucune dépendance : Python 3.8 ou plus suffit.
Utilisation :  python3 maj_matchs.py
"""
import datetime
import json
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

# --- Réglages ---------------------------------------------------------------
SAISON = "2026/2027"
COMITE = "PTPL49"  # Comité de volley du Maine-et-Loire
POULES = {
    # code poule FFVB : nom affiché sur le site
    "DSM": "Compétition libre masculine",
    "DS1": "Compétition libre mixte, 1re division",
    "DS2": "Compétition libre mixte, 2e division",
    "DS3": "Compétition libre mixte, 3e division",
}
COUPES = {
    # code division FFVB : nom affiché (compétitions à élimination, sans classement)
    "COF": "Coupe de l'Anjou féminine",
    "CDM": "Coupe de l'Anjou mixte",
    "COM": "Coupe de l'Anjou masculine",
}
SORTIE = Path(__file__).with_name("matchs.json")
URL = ("https://www.ffvbbeach.org/ffvbapp/resu/vbspo_calendrier.php"
       "?saison={saison}&codent={comite}&poule={poule}&calend=COMPLET")
URL_COUPE = ("https://www.ffvbbeach.org/ffvbapp/resu/vbspo_calendrier.php"
             "?saison={saison}&codent={comite}&division={division}")
# ---------------------------------------------------------------------------

RE_CODE = re.compile(r"^[A-Za-z][A-Za-z0-9]{1,6}\d{3}$")  # DS2A004, COMA008, mixA011, COM021
RE_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{2})$")
RE_HEURE = re.compile(r"^\d{1,2}:\d{2}$")
RE_SCORE = re.compile(r"^[0-3]$")
RE_TOTAL = re.compile(r"^\d{2,3}\s*-\s*\d{2,3}$")
RE_SET = re.compile(r"\d+\s*:\s*\d+")
RE_RANG = re.compile(r"^\d+\.?$")


class Lignes(HTMLParser):
    """Récupère toutes les lignes <tr> sous forme de listes de cellules texte."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lignes, self.pile = [], []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.pile.append([])
        elif tag in ("td", "th") and self.pile:
            self.pile[-1].append("")

    def handle_endtag(self, tag):
        if tag == "tr" and self.pile:
            self.lignes.append([c.strip() for c in self.pile.pop()])

    def handle_data(self, data):
        if self.pile and self.pile[-1]:
            self.pile[-1][-1] += " " + data

    def resultat(self):
        while self.pile:
            self.lignes.append([c.strip() for c in self.pile.pop()])
        return [[re.sub(r"\s+", " ", c) for c in l] for l in self.lignes]


def telecharger(poule, url=None):
    url = url or URL.format(saison=SAISON, comite=COMITE, poule=poule)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (site ASLM Volley-Ball, maj quotidienne)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        brut = r.read()
        charset = r.headers.get_content_charset() or "iso-8859-1"
    try:
        return brut.decode(charset)
    except (LookupError, UnicodeDecodeError):
        return brut.decode("iso-8859-1", errors="replace")


def entier(v):
    v = (v or "").strip().rstrip(".")
    return int(v) if v.isdigit() else 0


def lire_match(cellules):
    c = [x for x in cellules if x]
    if len(c) < 5 or not RE_CODE.match(c[0]):
        return None
    try:
        i_date = next(i for i, x in enumerate(c) if RE_DATE.match(x))
    except StopIteration:
        return None
    j, m, a = RE_DATE.match(c[i_date]).groups()
    reste = c[i_date + 1:]
    heure = ""
    if reste and RE_HEURE.match(reste[0]):
        heure, reste = reste[0], reste[1:]
    equipes, scores, sets, autres = [], [], "", []
    for x in reste:
        if RE_SCORE.match(x):
            scores.append(int(x))
        elif RE_TOTAL.match(x):
            continue
        elif RE_SET.search(x):
            sets = ", ".join(s.replace(" ", "") for s in RE_SET.findall(x))
        elif len(equipes) < 2:
            equipes.append(x)
        else:
            autres.append(x)
    if len(equipes) < 2 or any("xxxx" in e.lower() for e in equipes):
        return None  # équipe exempte ou ligne incomplète
    joue = len(scores) >= 2
    return {
        "code": c[0],
        "date": f"20{a}-{m}-{j}",
        "heure": heure.zfill(5),
        "dom": equipes[0],
        "ext": equipes[1],
        "sd": scores[0] if joue else None,
        "se": scores[1] if joue else None,
        "sets": sets if joue else "",
        "salle": "" if joue else (autres[0] if autres else ""),
    }


def lire_classement(lignes):
    """Ligne de classement : rang, équipe, points, joués, gagnés, perdus, forfaits,
    3-0, 3-1, 3-2, 2-3, 1-3, 0-3, sets pour, sets contre, ..."""
    classement = []
    for l in lignes:
        if any(RE_CODE.match(x) for x in l):
            continue  # ligne de match, pas de classement
        for k in range(len(l) - 14):
            if RE_RANG.match(l[k]) and re.search(r"[A-Za-z]", l[k + 1]) and not RE_CODE.match(l[k + 1]):
                v = l[k:]
                classement.append({
                    "rang": entier(v[0]), "equipe": v[1], "pts": entier(v[2]),
                    "j": entier(v[3]), "g": entier(v[4]), "p": entier(v[5]),
                    "sp": entier(v[13]), "sc": entier(v[14]),
                })
                break
    vus, propre = set(), []
    for e in classement:  # retire les doublons éventuels
        if e["equipe"] not in vus:
            vus.add(e["equipe"])
            propre.append(e)
    return propre


def lire_poule(code, nom):
    lignes = Lignes()
    lignes.feed(telecharger(code))
    lignes = lignes.resultat()
    matchs, vus = [], set()
    for l in lignes:
        m = lire_match(l)
        if m and m["code"] not in vus:
            vus.add(m["code"])
            matchs.append(m)
    return {
        "code": code,
        "nom": nom,
        "url": URL.format(saison=SAISON, comite=COMITE, poule=code).replace("&calend=COMPLET", ""),
        "classement": lire_classement(lignes),
        "matchs": matchs,
    }


RE_TOUR = re.compile(r"(tour|finale|coupe|challenge)", re.I)


def lire_coupe(code, nom):
    """Coupe : on garde l'intitulé du tour (ligne de titre) devant chaque match."""
    url = URL_COUPE.format(saison=SAISON, comite=COMITE, division=code)
    lignes = Lignes()
    lignes.feed(telecharger(code, url))
    matchs, vus, tour = [], set(), ""
    for l in lignes.resultat():
        cellules = [x for x in l if x]
        if len(cellules) == 1 and RE_TOUR.search(cellules[0]) and len(cellules[0]) < 60:
            tour = cellules[0]
            continue
        m = lire_match(l)
        if m and m["code"] not in vus:
            vus.add(m["code"])
            m["tour"] = tour
            matchs.append(m)
    return {"code": code, "nom": nom, "url": url, "matchs": matchs}


def main():
    ancien = {}
    if SORTIE.exists():
        try:
            ancien = {p["code"]: p for p in json.loads(SORTIE.read_text("utf-8")).get("poules", [])}
        except (ValueError, KeyError):
            pass
    poules, erreurs = [], 0
    for code, nom in POULES.items():
        try:
            p = lire_poule(code, nom)
            if not p["matchs"]:
                raise ValueError("aucun match trouvé (la page a peut-être changé)")
            print(f"{code} : {len(p['matchs'])} matchs, {len(p['classement'])} équipes au classement")
            poules.append(p)
        except Exception as e:  # on garde les données de la veille
            erreurs += 1
            print(f"{code} : ÉCHEC ({e}), données précédentes conservées", file=sys.stderr)
            if code in ancien:
                poules.append(ancien[code])
        time.sleep(2)  # reste poli avec le serveur de la fédération
    if erreurs == len(POULES):
        print("Aucune poule lue, matchs.json n'est pas modifié.", file=sys.stderr)
        return 1
    anciennes_coupes = {}
    try:
        anciennes_coupes = {c["code"]: c for c in json.loads(SORTIE.read_text("utf-8")).get("coupes", [])}
    except (OSError, ValueError, KeyError):
        pass
    coupes = []
    for code, nom in COUPES.items():
        try:
            c = lire_coupe(code, nom)
            if not c["matchs"]:
                raise ValueError("aucun match trouvé")
            print(f"{code} : {len(c['matchs'])} matchs de coupe")
            coupes.append(c)
        except Exception as e:
            print(f"{code} : ÉCHEC ({e}), données précédentes conservées", file=sys.stderr)
            if code in anciennes_coupes:
                coupes.append(anciennes_coupes[code])
        time.sleep(2)
    donnees = {
        "maj": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "saison": SAISON,
        "poules": poules,
        "coupes": coupes,
    }
    SORTIE.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), "utf-8")
    print(f"Écrit : {SORTIE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
