# Initialiser un plan de contrôle avec kubeadm

Lab guidé de la leçon kubeadm, module Installer un cluster du niveau 4 :
préparer un plan de contrôle remis à zéro (modules, routage IP, swap, paquets
figés) de façon durable, l'initialiser avec un fichier de configuration,
donner un kubeconfig à l'utilisateur, puis poser Calico jusqu'au nœud Ready. Le
nettoyage reconstruit le cluster du catalogue, worker compris, quel que soit
l'état laissé.

| | |
|---|---|
| Cible | `k8s-cp.lab` (et `k8s-w1.lab`, remis à zéro puis rendu au cluster), cluster kubeadm du catalogue |
| Durée | environ 45 minutes |
| Page associée | [kubeadm, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/kubeadm/#mettre-en-pratique) |

```bash
dsoxlab run   cka-initialiser-un-plan-de-controle
dsoxlab check cka-initialiser-un-plan-de-controle
```
