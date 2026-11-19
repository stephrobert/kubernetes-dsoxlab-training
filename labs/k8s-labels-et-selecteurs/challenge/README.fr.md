# Challenge : Étiqueter et sélectionner des Pods

## 📍 La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre kubectl le vise
déjà. Dans le namespace **`etiquettes`** :

- le Deployment **`web`** fait tourner trois Pods ;
- le Deployment **`api`** fait tourner deux Pods.

Aucun de ces Pods n'a de label `env`. Le fichier
**`~/etiquettes/releve.txt`** attend un sélecteur.

## 🎯 Ce que vous devez obtenir

1. **Tous les Pods de `web` ont le label `env=prod`**, et ils le gardent quand
   ils sont remplacés.

2. **Le Deployment `web` a une annotation `description`**, avec une phrase qui
   dit à quoi il sert.

3. Après **`selecteur`**, dans le fichier : un sélecteur de labels qui utilise
   une négation (`!=` ou `!clé`) et qui rend **exactement les Pods de `api`**.

## 🧭 Les repères utiles

Un label posé sur un Pod disparaît avec lui. Or les Pods d'un Deployment sont
remplacés souvent : à chaque mise à jour, à chaque suppression, à chaque panne
de nœud. Un label qui doit durer s'écrit donc dans le modèle de Pod du
Deployment. Un label posé sur le Deployment lui-même ne descend pas jusqu'aux
Pods.

Pour choisir entre un label et une annotation, demandez-vous si vous devrez un
jour choisir des objets par cette information. Une phrase de description ne
sert pas à choisir, et un label n'accepte pas d'espaces.

Essayez votre sélecteur avec `kubectl get pods -n etiquettes -l` avant de
l'écrire dans le fichier, et comptez les Pods qu'il rend. Attention : une
négation garde aussi les Pods qui n'ont pas du tout la clé. Écrivez le
sélecteur seul, tel qu'il suit `-l`.

## ✅ Comment vous saurez que c'est bon

Les tests lisent le modèle de Pod et les annotations de `web`. Ils rejouent
ensuite votre sélecteur tel quel et comparent les Pods rendus à ceux de `api`.

```bash
dsoxlab check k8s-labels-et-selecteurs
```
