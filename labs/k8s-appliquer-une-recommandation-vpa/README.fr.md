# Appliquer une recommandation du VPA

Lab guidé de la leçon « Vertical Pod Scaling », module 8 de la formation
Kubernetes : un Vertical Pod Autoscaler en mode Off sur un Deployment
sous-dimensionné, sa recommandation lue, puis des requests reportées à la main
entre ses bornes, sans qu'aucun Pod soit évincé.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab installe metrics-server v0.9.1 et le VPA 1.8.1, et pose le namespace `dimensionnement` |
| Durée | environ 25 minutes |
| Page associée | [Vertical Pod Scaling, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/vertical-pod-scaling/#mettre-en-pratique) |

Le `cleanup.yaml` retire le namespace, puis le VPA par son script officiel
(`hack/vpa-down.sh`) et metrics-server : le cluster revient à l'état du socle.

```bash
dsoxlab run   k8s-appliquer-une-recommandation-vpa
dsoxlab check k8s-appliquer-une-recommandation-vpa
```
