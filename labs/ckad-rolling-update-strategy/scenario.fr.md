# Régler une mise à jour progressive : maxSurge et maxUnavailable

## La situation

Dans le namespace **`lab`**, le Deployment **`webapp`** tourne en cinq
replicas, image `nginx:1.30.5`. La prochaine mise à jour doit passer en
`nginx:1.30.6`, et l'équipe a des contraintes : le cluster n'a pas de
place pour plus de **deux Pods en trop** pendant la bascule, et le service
ne tolère pas plus d'**un Pod indisponible** à la fois.

Le Deployment a été créé avec une stratégie explicite
**`strategy.type: Recreate`**, qui ne respecte ni l'une ni l'autre :
`Recreate` tue *tous* les Pods avant d'en démarrer un seul nouveau, le
service tombe donc pendant toute la bascule, et cette stratégie n'a ni
`maxSurge` ni `maxUnavailable` à régler.

## Ce que vous devez obtenir

1. Le Deployment `webapp` a une stratégie **`RollingUpdate`**, à la place du
   `Recreate` qu'il porte aujourd'hui.

2. Son `maxSurge` vaut **2**.

3. Son `maxUnavailable` vaut **1**.

4. Son image est passée à **`nginx:1.30.6`**.

5. Ses **cinq** replicas sont **prêts, à jour et sur la nouvelle image**.
   L'exercice change la stratégie et l'image, pas la taille du Deployment :
   il demande toujours cinq replicas, et c'est contrôlé ici aussi.

6. **Deux révisions de `webapp` existent**, produites par ce Deployment,
   celle de la nouvelle image venant après celle de l'ancienne dans
   l'historique.

7. Le ReplicaSet de `nginx:1.30.6` porte **cinq replicas prêts**.

8. Les anciens ReplicaSets sont **conservés à zéro**.

## Les repères utiles

`Recreate` et `RollingUpdate` sont les deux stratégies qu'un Deployment peut
porter, et seule la seconde remplace les Pods progressivement. C'est pour
cela que `maxSurge` et `maxUnavailable` vivent sous
`spec.strategy.rollingUpdate` : ils ne veulent dire quelque chose que si le
type vaut `RollingUpdate`.

Un Deployment garde ses anciens ReplicaSets, à zéro replica : c'est ce qui
permet le retour arrière, et c'est aussi ce qui montre qu'un remplacement a
eu lieu. Chaque déploiement donne au ReplicaSet qu'il active un numéro
`deployment.kubernetes.io/revision` plus élevé, et chacun de ces ReplicaSets
porte un `ownerReferences` qui désigne le Deployment qui l'a produit. Les
tests lisent les deux : un ReplicaSet écrit à la main n'est pas une
révision.

**Un conseil, et celui-là n'est pas noté.** Réglez la stratégie *avant* de
déclencher la mise à jour : c'est la stratégie en place à cet instant qui
pilote le remplacement. Rien ne peut le mesurer après coup, un Deployment ne
gardant aucune trace de la stratégie sous laquelle un déploiement passé s'est
joué. Le jour de l'examen, personne ne contrôlera l'ordre non plus, et une
bascule jouée sous la stratégie par défaut est une bascule pour laquelle le
cluster n'avait peut-être pas la place.

## Comment vous saurez que c'est bon

Les tests lisent la stratégie du Deployment, son image, son nombre de
replicas et ses replicas prêts, puis les ReplicaSets qui lui appartiennent,
avec leurs numéros de révision. Le nombre de replicas est lu en même temps
que l'état de la révision que le Deployment déclare active : être prêt, c'est
être prêt sur la nouvelle image, pas sur celle dont vous êtes parti.

```bash
dsoxlab check ckad-rolling-update-strategy
```
