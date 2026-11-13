# Lire les interfaces CRI, CNI et CSI d'un nœud

Lab guidé de la leçon « CNI, CSI et CRI », module Installer un cluster du
niveau 4 : sur un nœud kubeadm, lire le socket du runtime qu'emploie le kubelet, le
runtime annoncé à l'API, la configuration CNI en vigueur et les pilotes CSI du
cluster. Chaque réponse est comparée à la valeur réelle, relue sur le nœud.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue |
| Durée | environ 20 minutes |
| Page associée | [CNI, CSI et CRI, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cni-csi-cri/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-lire-les-interfaces-d-un-noeud
dsoxlab check k8s-lire-les-interfaces-d-un-noeud
```
