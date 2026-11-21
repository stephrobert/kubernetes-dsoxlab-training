# Challenge : Faire baisser le compte d'un audit CIS, et le vérifier par un second audit

## La situation

Le cluster sort d'une installation `kubeadm` par défaut. L'équipe conformité
demande un audit du worker **`k8s-w1.lab`** contre le **référentiel CIS**, et
la remédiation de ce qui peut l'être sans changer l'architecture.

**kube-bench** est l'outil qui fait cet audit. Son Job est déjà écrit, sur le
control plane, en `/root/kube-bench-job.yaml`. Il tourne sur `k8s-w1.lab`,
avec la cible `node` et les répertoires du nœud montés en lecture seule, et
écrit son rapport en JSON dans ses journaux.

## Ce que vous devez obtenir

1. Vous avez **lancé l'audit** du worker et lu ce qu'il lui reproche.

2. Les contrôles **4.1.1** et **4.1.9** passent. Ils portent des numéros
   différents et un même reproche : à vous de voir lequel, et sur quels
   fichiers.

3. Le **worker fonctionne toujours** : `k8s-w1.lab` est `Ready`.

4. Le compte **total** d'échecs du worker a baissé. Corriger un contrôle en
   cassant un autre ne compte pas.

## Les repères utiles

La remédiation se joue **sur le nœud audité**. Depuis le control plane,
`ssh k8s-w1.lab` y mène.

Le rapport de kube-bench est du JSON dans les journaux du Pod du Job. Chaque
contrôle porte son numéro, son intitulé, son état, et une section
`remediation` qui dit quoi faire.

Un Job qui a déjà tourné ne se relance pas : il faut le supprimer avant de le
recréer.

L'audit se relance autant de fois qu'on veut. C'est même la seule façon de
savoir si une correction a pris.

## Comment vous saurez que c'est bon

Les tests **relancent kube-bench** sur le worker et comptent. Ils ne relisent
pas un rapport que vous auriez laissé : un rapport s'édite, un audit qui tourne
sous nos yeux ne s'édite pas. Ils exigent que les deux contrôles visés
passent, que le total d'échecs ait baissé, et que le worker soit toujours
`Ready`.

```bash
dsoxlab check cks-cis-benchmark-remediate
```
