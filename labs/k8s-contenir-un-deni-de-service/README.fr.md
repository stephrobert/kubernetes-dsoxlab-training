# Contenir un déni de service dans son namespace

Lab guidé de la leçon « Déni de service : épuiser un cluster », module Modèle
de menaces et cadres de la formation Kubernetes (niveau 5, objectif KCSA
« Denial of Service »). Une charge sans limites tourne dans un namespace de
test : la plafonner par un ResourceQuota et un LimitRange, prouver le refus et
les valeurs par défaut par de vraies tentatives, borner la charge en marche, et
vérifier qu'une application d'un autre namespace continue de répondre.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab pose les namespaces `bac-a-sable` et `annuaire` |
| Durée | environ 30 minutes |
| Page associée | [Formation Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/), en attendant la publication de la leçon |

La charge abusive est sûre pour le nœud partagé, par construction : chacun de
ses deux Pods écrit un bloc fixe de 96 Mio dans un `emptyDir` en mémoire borné
à 128 Mio, puis occupe un processeur par rafales de 20 secondes. Jamais assez
pour mettre un nœud sous pression mémoire.

Le `cleanup.yaml` supprime les deux namespaces, quota et LimitRange compris :
rien n'est posé à l'échelle du cluster.

```bash
dsoxlab run   k8s-contenir-un-deni-de-service
dsoxlab check k8s-contenir-un-deni-de-service
```
