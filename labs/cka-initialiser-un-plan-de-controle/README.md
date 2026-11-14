# Initialise a control plane with kubeadm

Guided lab of the kubeadm lesson, Install a cluster module of level 4: prepare
a reset control plane (modules, IP forwarding, swap, held packages) so that it
lasts, initialise it with a configuration file, give the user a kubeconfig,
then install Calico until the node is Ready. Cleanup rebuilds the catalogue's
cluster, worker included, whatever state is left.

| | |
|---|---|
| Target | `k8s-cp.lab` (and `k8s-w1.lab`, reset then given back to the cluster), the catalogue's kubeadm cluster |
| Duration | about 45 minutes |
| Related page | [kubeadm, Mettre en pratique section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/kubeadm/#mettre-en-pratique) |

```bash
dsoxlab run   cka-initialiser-un-plan-de-controle
dsoxlab check cka-initialiser-un-plan-de-controle
```
