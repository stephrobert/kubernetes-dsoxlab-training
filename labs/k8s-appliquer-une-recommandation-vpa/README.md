# Apply a VPA recommendation

Guided lab of the "Vertical Pod Scaling" lesson, module 8 of the Kubernetes
course: a Vertical Pod Autoscaler in Off mode on an undersized Deployment, its
recommendation read, then requests reported by hand between its bounds, with no
Pod evicted.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab installs metrics-server v0.9.1 and VPA 1.8.1, and sets up the `dimensionnement` namespace |
| Duration | about 25 minutes |
| Related page | [Vertical Pod Scaling, Put into practice section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/vertical-pod-scaling/#mettre-en-pratique) |

The `cleanup.yaml` removes the namespace, then the VPA with its official script
(`hack/vpa-down.sh`) and metrics-server: the cluster returns to the foundation's state.

```bash
dsoxlab run   k8s-appliquer-une-recommandation-vpa
dsoxlab check k8s-appliquer-une-recommandation-vpa
```
