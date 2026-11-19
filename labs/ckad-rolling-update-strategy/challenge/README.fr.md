# Challenge : Régler une mise à jour progressive : maxSurge et maxUnavailable

## 📍 La situation

Vous êtes sur le control plane du cluster kubeadm, et votre kubectl est
configuré. Dans le namespace **`lab`**, le Deployment **`webapp`** tourne avec
cinq Pods, en `nginx:1.30.5`.

La prochaine mise à jour doit passer en `nginx:1.30.6`. L'équipe a deux
contraintes :

- le cluster n'a pas la place pour plus de **deux Pods en trop** pendant la
  bascule ;
- le service ne supporte pas plus d'**un Pod indisponible** à la fois.

Or `webapp` a été créé avec la stratégie **`Recreate`**. Elle arrête tous les
Pods avant d'en démarrer un seul nouveau : le service tombe pendant toute la
bascule. Et elle n'a ni `maxSurge` ni `maxUnavailable` à régler.

## 🎯 Ce que vous devez obtenir

1. Le Deployment `webapp` a la stratégie **`RollingUpdate`**, à la place de
   `Recreate`.

2. Son `maxSurge` vaut **2**.

3. Son `maxUnavailable` vaut **1**.

4. Son image est passée à **`nginx:1.30.6`**.

5. Ses **cinq** Pods sont **prêts, à jour et sur la nouvelle image**. Vous
   changez la stratégie et l'image, pas le nombre de Pods : il en faut
   toujours cinq.

6. **Deux révisions de `webapp` existent**, créées par ce Deployment. Celle de
   la nouvelle image vient après celle de l'ancienne.

7. Le ReplicaSet de `nginx:1.30.6` a **cinq Pods prêts**.

8. Les anciens ReplicaSets sont **gardés, à zéro Pod**.

## 🧭 Les repères utiles

`maxSurge` et `maxUnavailable` se rangent sous `spec.strategy.rollingUpdate`.
Ils n'ont de sens qu'avec le type `RollingUpdate`.

Un Deployment garde ses anciens ReplicaSets, à zéro Pod. Chaque changement
d'image donne au nouveau ReplicaSet un numéro de révision plus grand
(l'annotation `deployment.kubernetes.io/revision`). Chaque ReplicaSet désigne
aussi le Deployment qui l'a créé (le champ `ownerReferences`). Les tests lisent
les deux : un ReplicaSet écrit à la main ne compte pas comme une révision.

**Un conseil, qui n'est pas noté :** réglez la stratégie **avant** de changer
l'image. C'est la stratégie en place au moment du changement qui décide comment
les Pods sont remplacés. Aucun test ne peut le vérifier après coup : un
Deployment ne garde pas trace de la stratégie utilisée lors d'une bascule
passée.

## ✅ Comment vous saurez que c'est bon

Les tests lisent la stratégie du Deployment, son image, son nombre de Pods et
ses Pods prêts. Ils lisent ensuite les ReplicaSets qui lui appartiennent, avec
leurs numéros de révision. Les Pods prêts doivent l'être sur la nouvelle
image, pas sur l'ancienne.

```bash
dsoxlab check ckad-rolling-update-strategy
```
