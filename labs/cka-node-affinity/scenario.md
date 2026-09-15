# Placer avec nodeAffinity : contrainte obligatoire et préférence

## La situation

L'application **`storage-app`** écrit beaucoup et ne doit tourner que sur
des nœuds à disques rapides, `ssd` ou `nvme`. Parmi eux, l'équipe préfère
ceux qui portent le label `storage-tier=fast`, sans en faire une
obligation. Un seul nœud du cluster a des disques rapides :
**`k8s-w1.lab`**, qu'il faut étiqueter.

Une seconde application, **`gpu-app`**, exige un accélérateur que le
cluster n'a pas encore : elle doit être déclarée dès maintenant, attendre,
puis démarrer d'elle-même le jour où un nœud sera étiqueté.

Vous êtes sur le control plane, avec `kubectl` configuré. Le namespace
**`lab`** existe.

## Ce que vous devez obtenir

1. Le nœud `k8s-w1.lab` porte le label **`disktype=ssd`**.

2. Un Deployment **`storage-app`** dans `lab`, trois replicas, image
   `nginx:1.27-alpine`, avec une affinité de nœud **obligatoire** sur
   `disktype` valant `ssd` **ou** `nvme`, et une affinité **préférée** de
   poids **80** sur `storage-tier=fast`. Ses trois Pods tournent.

3. Un Pod **`gpu-app`** dans `lab`, image `nginx:1.27-alpine`, avec une
   affinité de nœud obligatoire sur **`accelerator=gpu`**. Déclaré avant
   que le label existe, il reste `Pending`.

4. Le label **`accelerator=gpu`** posé sur `k8s-w1.lab` : `gpu-app` passe
   `Running` sans avoir été recréé.

## Les repères utiles

`nodeAffinity` distingue ce qui est **obligatoire** au placement de ce qui
est **préféré** ; les deux ont un nom long qui finit par
`IgnoredDuringExecution`, et c'est ce suffixe qui dit qu'un Pod déjà placé
ne bouge pas si le label change ensuite. Les opérateurs `In`, `NotIn`,
`Exists` permettent plus qu'une égalité.

Un Pod `Pending` pour affinité le dit dans `kubectl describe pod`, avec le
nombre de nœuds qui ne correspondent pas. Le scheduler réessaie de lui-même
dès qu'un nœud change.

## Comment vous saurez que c'est bon

Les tests lisent les labels des nœuds, les affinités déclarées par
`storage-app` et `gpu-app`, et le nœud réel de chacun de leurs Pods.

```bash
dsoxlab check cka-node-affinity
```
