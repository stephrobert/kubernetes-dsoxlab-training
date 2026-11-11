# Un Pod à deux conteneurs et ses budgets de ressources

## La situation

L'équipe veut livrer dans le namespace **`lab`** un Pod **`multi-app`** qui
embarque deux conteneurs : le serveur web, et un petit collecteur qui tourne à
côté. Le cluster est partagé, et la règle du namespace est claire : chaque
conteneur déclare ce qu'il demande et ce qu'il ne dépassera pas.

## Ce que vous devez obtenir

1. Un Pod **`multi-app`** dans `lab`, en `Running`, avec exactement deux
   conteneurs.

2. Le conteneur **`web`**, image `nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`, demande `100m` de CPU et `64Mi` de
   mémoire, et se limite à `200m` et `128Mi`.

3. Le conteneur **`logger`**, image `busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`, tourne en boucle sans fin,
   demande `50m` et `32Mi`, et se limite à `100m` et `64Mi`.

4. Dans chaque conteneur, **la limite de mémoire que le noyau applique** est
   celle que vous avez déclarée.

## Les repères utiles

Les budgets se déclarent conteneur par conteneur, jamais au niveau du Pod. Une
limite de mémoire n'est pas un vœu : le noyau l'applique, et on peut la lire
depuis l'intérieur du conteneur, dans son cgroup.

`kubectl run` génère un Pod à un conteneur ; pour deux, il faut écrire le YAML,
et `--dry-run=client -o yaml` donne un point de départ.

## Comment vous saurez que c'est bon

Les tests lisent la définition du Pod, puis entrent dans chaque conteneur pour
lire la limite de mémoire que le noyau applique réellement.

```bash
dsoxlab check ckad-pod-resources-labels
```
