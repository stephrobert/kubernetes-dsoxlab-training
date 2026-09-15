# Un Pod à deux conteneurs, avec budgets, labels et annotation

## La situation

L'équipe veut livrer dans le namespace **`lab`** un Pod **`multi-app`** qui
embarque deux conteneurs : le serveur web, et un petit collecteur qui tourne
à côté. Le cluster est partagé, et la règle du namespace est claire : chaque
conteneur déclare ce qu'il demande et ce qu'il ne dépassera pas. Les labels
servent aux Services et aux sélections, l'annotation sert aux humains.

## Ce que vous devez obtenir

1. Un Pod **`multi-app`** dans `lab`, en `Running`, avec exactement deux
   conteneurs.

2. Le conteneur **`web`**, image `nginx:1.27-alpine`, demande `100m` de CPU
   et `64Mi` de mémoire, et se limite à `200m` et `128Mi`.

3. Le conteneur **`logger`**, image `busybox:1.36`, tourne en boucle sans
   fin, demande `50m` et `32Mi`, et se limite à `100m` et `64Mi`.

4. Le Pod porte les labels `app=multi-app`, `tier=frontend` et `version=v1`,
   et une annotation **`description`**, dont vous choisissez le texte.

## Les repères utiles

Les `resources` se déclarent conteneur par conteneur, jamais au niveau du
Pod. Une limite de mémoire n'est pas un vœu : le noyau l'applique, et on
peut la lire depuis l'intérieur du conteneur.

`kubectl run` génère un Pod à un conteneur ; pour deux, il faut écrire le
YAML, et `--dry-run=client -o yaml` donne un point de départ.

## Comment vous saurez que c'est bon

Les tests lisent la définition du Pod, puis ils entrent dans chaque
conteneur pour lire la limite de mémoire que le noyau applique réellement.

```bash
dsoxlab check ckad-pod-resources-labels
```
