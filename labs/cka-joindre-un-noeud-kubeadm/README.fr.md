# Joindre un worker à un cluster kubeadm

Lab guidé de la leçon « Joindre un nœud », module Installer un cluster du niveau
4 : préparer un worker réinitialisé (swap, pilote de cgroup de containerd,
paquets figés), le joindre avec la commande du plan de contrôle, vérifier qu'il
est Ready avec le bon kubelet, puis y forcer un Pod. Le nettoyage rend le
worker au cluster, quel que soit l'état laissé.

| | |
|---|---|
| Cible | `k8s-cp.lab` et `k8s-w1.lab`, cluster kubeadm du catalogue |
| Durée | environ 30 minutes |
| Page associée | [Joindre un nœud, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/kubeadm-joindre-un-noeud/#mettre-en-pratique) |

```bash
dsoxlab run   cka-joindre-un-noeud-kubeadm
dsoxlab check cka-joindre-un-noeud-kubeadm
```
