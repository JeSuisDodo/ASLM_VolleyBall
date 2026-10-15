# Site ASLM Volley-Ball

## Mise en ligne sur OVH (remplace l'ancien WordPress)
1. Sauvegarder l'ancien site : dans le dossier `www` (FTP), renommer `www` en `www-wordpress` ou télécharger son contenu.
2. Envoyer dans `www` : `index.html`, `matchs.json`, `.htaccess`.
3. Ouvrir https://volley-lacdemaine.org et vérifier chaque page.

Le fichier `.htaccess` force le HTTPS et redirige les anciennes adresses WordPress vers les nouvelles pages.

# Mise à jour automatique des matchs

## Contenu du dossier
- `index.html` : le site complet.
- `matchs.json` : les matchs et classements, lus par la page Matchs.
- `maj_matchs.py` : lit les pages de la FFvolley et réécrit `matchs.json`.
- `.github/workflows/maj-matchs.yml` : lance le script une fois par jour (vers 7 h).

Si `matchs.json` est absent ou illisible, le site affiche la copie intégrée à `index.html`.
Si la FFvolley ne répond pas un jour donné, le script garde les données de la veille.

## Mise en place (une seule fois)
1. Créer un compte sur github.com, puis un dépôt (privé ou public).
2. Y déposer tout le contenu de ce dossier, y compris le dossier `.github`.
3. Dans le dépôt : Settings > Secrets and variables > Actions > New repository secret, créer :
   - `FTP_HOST` : serveur FTP OVH (ex. `ftp.clusterXXX.hosting.ovh.net`, visible dans l'espace client OVH > Hébergement > FTP-SSH)
   - `FTP_USER` : identifiant FTP
   - `FTP_PASS` : mot de passe FTP
4. Onglet Actions > « Mise à jour des matchs » > Run workflow, pour tester tout de suite.

Ensuite, tout est automatique : chaque matin, `matchs.json` est mis à jour et envoyé dans le dossier `www` de l'hébergement.

## Ajouter une poule
Dans `maj_matchs.py`, ajouter une ligne dans `POULES` avec le code de la poule
(la valeur `poule=` de l'adresse FFvolley), par exemple : `"DS1": "Championnat départemental mixte, 1re division",`.

## Nouvelle saison
Changer `SAISON = "2026/2027"` dans `maj_matchs.py`.
