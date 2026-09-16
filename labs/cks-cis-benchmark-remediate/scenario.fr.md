# Faire baisser le compte d'un audit CIS, et le prouver par un second audit

## La situation

Le cluster sort d'une installation `kubeadm` par défaut. L'équipe conformité
demande un audit contre le **référentiel CIS**, et la remédiation de ce qui
peut l'être sans changer l'architecture.

**kube-bench** est l'outil qui fait cet audit. Son Job est déjà écrit, sur le
nœud, en `/root/kube-bench-job.yaml`. Il tourne dans le cluster, avec les
répertoires du nœud montés en lecture seule, et écrit son rapport en JSON dans
ses journaux.

## Ce que vous devez obtenir

1. Vous avez **lancé l'audit** et lu ce qu'il reproche au control plane.

2. Les contrôles **1.2.15**, **1.3.2** et **1.4.1** passent. Ils portent des
   numéros différents et un même reproche : à vous de voir lequel, et à quels
   composants.

3. Le **control plane fonctionne toujours** : `kubectl get nodes` répond et
   les Pods de `kube-system` sont revenus en `Running`.

4. Le compte **total** d'échecs a baissé. Corriger un contrôle en cassant un
   autre ne compte pas.

## Les repères utiles

Les trois composants visés sont des **Pods statiques** : leurs définitions
sont des fichiers du nœud, sous `/etc/kubernetes/manifests/`, et le kubelet
les surveille. Modifier un fichier suffit à redéployer le Pod.

Le rapport de kube-bench est du JSON dans les journaux du Pod du Job. Chaque
contrôle porte son numéro, son intitulé, son état, et une section
`remediation` qui dit quoi faire.

Un Job qui a déjà tourné ne se relance pas : il faut le supprimer avant de le
recréer.

L'audit se relance autant de fois qu'on veut. C'est même la seule façon de
savoir si une correction a pris.

## Comment vous saurez que c'est bon

Le dernier test **relance kube-bench** et compte. Il ne relit pas un rapport
que vous auriez laissé : un rapport s'édite, un audit qui tourne sous nos yeux
ne s'édite pas. Il exige que les trois contrôles visés passent, et que le
total d'échecs ait baissé.

```bash
dsoxlab check cks-cis-benchmark-remediate
```
