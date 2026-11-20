# Drain, maintain and bring a node back into service, then upgrade the cluster

Challenge of the **Maintain and upgrade** module of the Kubernetes course
(level 4), in the Put into practice section of the "Upgrade a cluster" lesson:
a disruption budget to set, a worker to empty then bring back, a record of the
operation, the whole cluster to upgrade from 1.36.4 to 1.37.0 without losing
the application, and a change made live to carry into the git repository.
Seven requirements, threshold 70, two blocking.

Like `cka-kubeadm-upgrade`, this challenge rebuilds the cluster one minor
version back at setup, and gives it back its version at cleanup.

| | |
|---|---|
| Target | `k8s-cp.lab` and `k8s-w1.lab`, the catalogue's kubeadm cluster; the lab sets up the `maintenance` namespace and the `~/maintenance` repository |
| Duration | about 60 minutes |
| Related page | [Upgrade a cluster](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/upgrade-a-kubernetes-cluster/) |

```bash
dsoxlab run    k8s-challenge-maintenir-un-noeud
dsoxlab check  k8s-challenge-maintenir-un-noeud
dsoxlab submit k8s-challenge-maintenir-un-noeud
```
