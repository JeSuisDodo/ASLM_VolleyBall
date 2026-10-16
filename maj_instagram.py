#!/usr/bin/env python3
"""
Récupère les 3 dernières publications du compte Instagram du club
et les enregistre pour le site (instagram.json + images dans le dossier insta/).

Lancé une fois par jour par .github/workflows/maj-matchs.yml.
Instagram limite fortement les accès sans connexion : si la lecture échoue,
le script garde les publications de la veille et ne bloque pas le reste.
Aucune dépendance : Python 3.8 ou plus suffit.
"""
import datetime
import json
import sys
import urllib.request
from pathlib import Path

COMPTE = "aslmvolley"
NOMBRE = 3
ICI = Path(__file__).parent
SORTIE = ICI / "instagram.json"
DOSSIER = ICI / "insta"
URL = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={COMPTE}"
ENTETES = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "x-ig-app-id": "936619743392459",  # identifiant public de l'application web Instagram
    "Accept": "application/json",
}


def lire(url, binaire=False):
    req = urllib.request.Request(url, headers=ENTETES)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return data if binaire else json.loads(data.decode("utf-8"))


def extraire(profil):
    """Transforme la réponse d'Instagram en liste simple de publications."""
    user = profil["data"]["user"]
    posts = []
    for edge in user["edge_owner_to_timeline_media"]["edges"][:NOMBRE]:
        n = edge["node"]
        legendes = n.get("edge_media_to_caption", {}).get("edges", [])
        posts.append({
            "code": n["shortcode"],
            "url": f"https://www.instagram.com/p/{n['shortcode']}/",
            "image_source": n.get("thumbnail_src") or n["display_url"],
            "legende": legendes[0]["node"]["text"] if legendes else "",
            "date": datetime.datetime.fromtimestamp(n["taken_at_timestamp"], datetime.timezone.utc).date().isoformat(),
            "video": bool(n.get("is_video")),
        })
    return posts


def main():
    try:
        posts = extraire(lire(URL))
        if not posts:
            raise ValueError("aucune publication trouvée")
        DOSSIER.mkdir(exist_ok=True)
        gardes = set()
        for p in posts:
            # les liens d'images Instagram expirent : on enregistre une copie dans le dépôt
            fichier = DOSSIER / f"{p['code']}.jpg"
            if not fichier.exists():
                fichier.write_bytes(lire(p.pop("image_source"), binaire=True))
            else:
                p.pop("image_source")
            p["image"] = f"insta/{fichier.name}"
            gardes.add(fichier.name)
        for ancien in DOSSIER.glob("*.jpg"):
            if ancien.name not in gardes:
                ancien.unlink()
        donnees = {
            "maj": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "compte": COMPTE,
            "posts": posts,
        }
        SORTIE.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), "utf-8")
        print(f"Instagram : {len(posts)} publications enregistrées")
    except Exception as e:  # Instagram a refusé ou changé de format : on garde la veille
        print(f"Instagram : ÉCHEC ({e}), publications précédentes conservées", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
