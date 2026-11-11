# Épreuve du niveau 1 : livrer et mettre à jour une application

## La situation

La boutique vous confie sa vitrine, sur le cluster kind **`boutique`** que
votre `kubectl` vise déjà. Le cahier des charges dit ce qu'il faut obtenir, pas
comment : c'est à vous de choisir les ressources. Au même moment, l'équipe de
l'entrepôt vous signale que son composant **`stock`**, dans l'espace
**`entrepot`**, ne démarre plus.

Les deux versions de la vitrine :

```text
version 1 : nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
version 2 : nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## Le cahier des charges

- La vitrine vit dans l'espace de son équipe, **`livraison`**, que vous créez,
  et **rien** d'elle ne traîne dans l'espace par défaut.
- Elle tourne en **trois exemplaires**, qui se remplacent seuls si l'un d'eux
  disparaît. Elle est livrée d'abord en **version 1**.
- Elle répond en HTTP à l'adresse **`http://vitrine.livraison`** depuis
  n'importe quel Pod du cluster.
- Elle reçoit son message d'accueil, `Bienvenue`, dans la variable
  **`MESSAGE_ACCUEIL`**, et le mot de passe de sa base, `Boutique-2026`, dans
  la variable **`DB_PASSWORD`**. Configuration et mot de passe vivent **hors de
  l'image** et sont gérés **à part** de la vitrine ; le mot de passe n'apparaît
  **jamais en clair** dans sa description.
- Elle passe ensuite en **version 2**, sans qu'aucun exemplaire ne manque
  pendant la bascule, et en gardant la possibilité de **revenir à la
  version 1**.
- Le composant **`stock`** tourne de nouveau. Son seuil vaut **`10`**. Avant
  toute réparation, écrivez dans **`~/epreuve/cause-stock.txt`** pourquoi il ne
  démarre pas et ce qu'il cherche sans le trouver, puis n'y touchez plus. Ce qu'il
  lit aujourd'hui, il doit le lire encore après la réparation.

## Comment vous serez noté

L'épreuve est notée sur l'**état final du cluster** et sur le fichier de la
cause, jamais sur les commandes tapées. Elle compte **sept critères**, qui
pèsent tous autant. Le seuil est de **70 sur 100**, et **cinq critères sont
critiques** : ils doivent tous réussir, quel que soit le total. Ce sont la
vitrine en version 2 sur trois exemplaires, l'adresse qui répond, la
configuration et le mot de passe hors de l'image, le retour à la version 1
resté possible, et le composant `stock` réparé après que sa cause a été
consignée.

Aucune procédure n'est donnée : les leçons du niveau 1 ont tout enseigné.

```bash
dsoxlab check  k8s-epreuve-livrer-et-mettre-a-jour
dsoxlab submit k8s-epreuve-livrer-et-mettre-a-jour
```
