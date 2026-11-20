# Vider, maintenir et remettre en service un nœud, puis monter le cluster de version

Challenge du module **Maintenir et mettre à jour** de la formation Kubernetes
(niveau 4), dans la section Mettre en pratique de la leçon « Mettre à jour un
cluster » : un budget de perturbation à poser, un worker à vider puis à rendre,
la trace de l'opération, tout le cluster à monter de 1.36.4 en 1.37.0 sans
perdre l'application, et une modification faite en direct à reporter dans le
dépôt git. Sept exigences, seuil 70, deux bloquantes.

Comme `cka-kubeadm-upgrade`, ce challenge reconstruit le cluster une version
mineure en arrière au setup, et le rend à sa version au nettoyage.

| | |
|---|---|
| Cible | `k8s-cp.lab` et `k8s-w1.lab`, cluster kubeadm du catalogue ; le lab pose le namespace `maintenance` et le dépôt `~/maintenance` |
| Durée | environ 60 minutes |
| Page associée | [Mettre à jour un cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/mettre-a-jour-cluster-kubernetes/) |

```bash
dsoxlab run    k8s-challenge-maintenir-un-noeud
dsoxlab check  k8s-challenge-maintenir-un-noeud
dsoxlab submit k8s-challenge-maintenir-un-noeud
```
