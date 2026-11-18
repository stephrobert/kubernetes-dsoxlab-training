# Relier deux clusters avec Cilium ClusterMesh

Lab guidé de la leçon « Relier deux clusters avec ClusterMesh », niveau 6
« Réseau avancé » de la formation Kubernetes (CKNE). Relier deux clusters
Cilium d'un nœud qui partagent une autorité de certification, rendre un Service
global, et prouver qu'un Pod du premier cluster atteint les backends des deux.

| | |
|---|---|
| Cible | `ha-cp1.lab` (cluster-1) et `ha-cp2.lab` (cluster-2), deux hôtes optionnels, un cluster d'un nœud chacun |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (qui déclare Kubernetes 1.33 à 1.36), CLI cilium v0.20.3, Helm 4.3.2 |
| Durée | environ 30 minutes, plus le setup qui construit les deux clusters |
| Prérequis | le lab `k8s-installer-cilium-sans-kube-proxy` |
| Page liée | [ClusterMesh](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/clustermesh/) |

Le `run` de ce lab monte `ha-cp1.lab` et `ha-cp2.lab` s'ils ne tournent pas
encore, les remet à zéro, construit les deux clusters et installe Cilium sur
les deux avec la même autorité de certification. Le `cleanup.yaml` remet les
deux nœuds à l'état « prêts, sans cluster », celui qu'attend aussi le lab
`cka-control-plane-haute-disponibilite` sur ces hôtes.

```bash
dsoxlab run   k8s-relier-deux-clusters
dsoxlab check k8s-relier-deux-clusters
```
