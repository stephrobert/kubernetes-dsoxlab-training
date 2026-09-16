# Remplacer une image criblée de failles, et le prouver par un second scan

## La situation

Dans le namespace **`chaine-appro`**, le Deployment **`web`** tourne en deux
exemplaires sur l'image **`nginx:1.21`**, publiée en 2021. Il sert les mêmes
pages qu'une image récente, personne ne s'en plaint, et rien dans le cluster
ne signale ce qu'elle traîne.

**Trivy** est installé sur le nœud, et sa base de vulnérabilités est déjà
téléchargée.

## Ce que vous devez obtenir

1. Vous avez **analysé** l'image en production et mesuré ce qu'elle porte.

2. Le Deployment `web` tourne sur une **autre version de nginx**, qui porte
   **strictement moins** de failles critiques. Le choix vous appartient, mais
   il devra se justifier par un scan, pas par la date de publication.

3. Les **deux exemplaires tournent** après le changement. Une image plus
   récente peut changer de port d'écoute ou d'utilisateur par défaut.

4. Vous ne changez pas d'application : c'est nginx qu'il faut mettre à jour.

## Les repères utiles

`trivy image <image>` analyse une image et classe ce qu'il trouve par
sévérité. L'option `--severity` restreint la sortie, `--quiet` retire la barre
de progression, et `--format json` donne de quoi compter.

Scannez **avant** de déployer. Déployer puis scanner, c'est scanner en
production, et c'est exactement ce que la chaîne d'approvisionnement cherche à
éviter.

Une image plus récente n'est pas toujours celle qui porte le moins. Les
variantes construites sur Alpine embarquent beaucoup moins de paquets que
celles basées sur Debian, et chaque paquet absent est une faille en moins.

Aucun outil ne dit qu'une image est « sûre ». Il dit ce qu'il **sait** au
moment où il regarde, avec la base du jour.

## Comment vous saurez que c'est bon

Le dernier test scanne **les deux** images, celle d'origine et la vôtre, au
même instant et avec la même base, puis exige strictement moins de failles
critiques dans la seconde. Un seuil fixe serait faux dès la semaine suivante :
la base s'enrichit tous les jours, et une image irréprochable aujourd'hui
compte des failles demain sans avoir changé d'un octet.

```bash
dsoxlab check cks-image-scanning-trivy
```
