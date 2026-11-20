# Bring live changes back to the Git repository

Challenge of the Kubernetes training, in the Put it into practice section of
the "kubectl edit, patch and replace" lesson: find the changes made live on a
cluster, carry into Git the one the team keeps, undo the others, without
recreating any object. Five requirements, pass mark 80%, two of them
blocking.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster; the lab sets up the `annuaire` namespace and the `~/annuaire` repository |
| Duration | about 35 minutes |
| Related pages | [kubectl edit, patch and replace](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-edit-patch-replace/#put-it-into-practice), [kubectl create and apply](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-create-apply/) |

```bash
dsoxlab run    k8s-challenge-ramener-le-cluster-au-depot
dsoxlab check  k8s-challenge-ramener-le-cluster-au-depot
dsoxlab submit k8s-challenge-ramener-le-cluster-au-depot
```
