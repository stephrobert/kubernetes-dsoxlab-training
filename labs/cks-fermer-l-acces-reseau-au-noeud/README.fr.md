# Fermer un worker au réseau, sauf les flux dont Kubernetes a besoin

Lab **CKS**, domaine *System Hardening* (10 % de l'épreuve), compétence
« Minimize external access to the network ».

Un pare-feu d'hôte sur un nœud Kubernetes doit fermer le reste sans couper le
kubelet, le plugin réseau ni l'administration, et sans effacer les règles que
kube-proxy et Calico écrivent eux-mêmes. Ce lab vous fait écrire cette chaîne,
la charger sans vous enfermer dehors, et la faire survivre à un redémarrage.

| | |
|---|---|
| Cible | `k8s-w2.lab`, second worker du cluster kubeadm (hôte optionnel), joint depuis `k8s-cp.lab` |
| Durée | environ 35 minutes |
| Leçon jumelée | [Durcir les nœuds](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/) |

```bash
dsoxlab run   cks-fermer-l-acces-reseau-au-noeud
dsoxlab check cks-fermer-l-acces-reseau-au-noeud
```

La vérification redémarre `k8s-w2.lab` : comptez deux minutes de plus.
