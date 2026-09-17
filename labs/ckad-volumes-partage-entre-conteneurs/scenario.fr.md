# Faire lire à un conteneur ce qu'un autre écrit, et pas le reste

## La situation

Dans le namespace **`journalisation`**, le Pod **`collecteur`** porte deux conteneurs.

Le conteneur **`producteur`** écrit une ligne toutes les cinq secondes dans
`/var/trace/messages`. Le conteneur **`lecteur`** est censé relire ce fichier
pour l'expédier ailleurs, et il ne trouve rien.

Les deux sont pourtant dans le même Pod. Ils partagent le réseau et l'adresse
IP, mais chacun garde le système de fichiers de son image.

## Ce que vous devez obtenir

1. Le conteneur `lecteur` voit le fichier `/var/trace/messages`, et il n'est pas
   vide.

2. Ce qui est écrit **ailleurs** par le producteur, hors de ce répertoire, reste
   invisible au lecteur.

3. Le Pod s'appelle toujours `collecteur`, et ses deux conteneurs gardent leurs
   noms.

Rien ne doit être conservé après la disparition du Pod : il s'agit de faire
passer, pas de stocker.

## Les repères utiles

Ce qu'il faut ajouter se déclare à **deux** niveaux : l'objet lui-même, une fois
pour le Pod, puis son montage dans chaque conteneur qui doit le voir. Déclarer
sans monter ne fait rien, et monter d'un seul côté ne partage rien.

Le type qui convient ici **naît avec le Pod et meurt avec lui**. Il ne sert pas
à conserver, mais à faire passer, et il ne demande aucun stockage préparé
d'avance.

Le chemin de montage doit être le même des deux côtés.

Les volumes d'un Pod ne se modifient pas à chaud : il faut le recréer.

## Comment vous saurez que c'est bon

Le dernier test exerce **les deux côtés**. Il vérifie que le fichier traverse,
puis il fait écrire le producteur **hors** du répertoire partagé et vérifie que
ce second fichier **ne traverse pas**. Monter le volume trop haut, sur la racine
ou sur `/tmp`, ferait passer la première moitié et échouer la seconde.

```bash
dsoxlab check ckad-volumes-partage-entre-conteneurs
```
