# Régler une mise à jour progressive : maxSurge et maxUnavailable

## La situation

Dans le namespace **`lab`**, le Deployment **`webapp`** tourne en cinq
replicas, image `nginx:1.26-alpine`. La prochaine mise à jour doit passer en
`nginx:1.27-alpine`, et l'équipe a des contraintes : le cluster n'a pas de
place pour plus de **deux Pods en trop** pendant la bascule, et le service
ne tolère pas plus d'**un Pod indisponible** à la fois.

Le Deployment a été créé avec la stratégie par défaut, qui ne respecte ni
l'une ni l'autre.

## Ce que vous devez obtenir

1. Le Deployment `webapp` a une stratégie **`RollingUpdate`** avec
   `maxSurge` à **2** et `maxUnavailable` à **1**.

2. Son image est passée à **`nginx:1.27-alpine`**.

3. La mise à jour est **terminée** : cinq replicas prêts sur la nouvelle
   image, et l'ancien ReplicaSet réduit à zéro.

## Les repères utiles

La stratégie se règle avant de déclencher la mise à jour, sinon c'est la
stratégie par défaut qui pilote le remplacement. Régler puis mettre à jour,
dans cet ordre.

Un Deployment garde ses anciens ReplicaSets, à zéro replica : c'est ce qui
permet le retour arrière, et c'est aussi ce qui prouve qu'une mise à jour a
eu lieu.

## Comment vous saurez que c'est bon

Les tests lisent la stratégie du Deployment, son image et ses replicas
prêts, puis ses ReplicaSets, ancien et nouveau.

```bash
dsoxlab check ckad-rolling-update-strategy
```
