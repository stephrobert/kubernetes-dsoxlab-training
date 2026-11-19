# Challenge : Modifier un Deployment en production sans perdre un conteneur, et résorber la dérive

## La situation

Dans le namespace **`magasin`**, le Deployment **`web`** porte **deux
conteneurs** : le serveur `web` et un agent de journaux `log-agent`. Son
manifeste versionné, la version « Git », est dans votre répertoire :
**`~/magasin/web.yaml`**.

Ce matin, pendant un **pic de charge**, un opérateur a monté `web` à **quatre
réplicas** directement dans le cluster, sans toucher au fichier. Le pic dure
encore. Puis un incident est ouvert, la référence **`INC-2026-0142`**, et
l'équipe vous demande trois corrections en direct.

Vous êtes sur le control plane, avec `kubectl` configuré.

## Ce que vous devez obtenir

1. Le conteneur `web` tourne en
   **`nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`**,
   le conteneur **`log-agent` est toujours là**, et le Deployment reste **le
   même objet** : pas de suppression suivie d'une recréation.
2. Le Deployment porte l'annotation **`incident-ref=INC-2026-0142`**.
3. Le conteneur `log-agent` a la variable d'environnement
   **`LOG_LEVEL=debug`**.
4. La **dérive** est résorbée : `kubectl diff -f ~/magasin/web.yaml` ne voit
   plus aucun écart et rend le code 0, et `web` tourne toujours avec ses
   **quatre réplicas**.

## Les repères

`kubectl patch` ne touche que les champs qu'il nomme, et son type compte sur
les **listes** : le strategic merge, par défaut, retrouve un conteneur par son
nom ; le JSON merge remplace la liste entière par celle du patch ; le JSON
patch vise un élément par son index. `kubectl replace --force` supprime puis
recrée l'objet : il arrête tous les Pods d'un coup.

Sauvegardez l'état actuel avant de modifier. Une modification faite dans le
cluster sans être reportée dans Git sera défaite par le prochain
`kubectl apply` du fichier. `kubectl diff -f` montre l'écart, en `-` la valeur
vivante et en `+` celle du fichier ; c'est le fichier qu'il faut mettre à jour,
pas le cluster qu'il faut ramener en arrière.

## Comment vous saurez que ça marche

Les tests lisent le Deployment (image, conteneurs, identité de l'objet,
annotation, variable), attendent la fin du rollout, puis lancent
`kubectl diff` sur votre manifeste.

```bash
dsoxlab check k8s-modifier-une-ressource-en-production
```
