# Repair a node's Pod network and read what the network says

**CKA** lab, *Troubleshooting* domain (30 % of the exam). Guided lab of the
"Pod Networking" lesson of the Kubernetes course, whose gestures it practises:
read the address ranges, reach a Pod on another node, repair a node whose Pod
network went down, tell an immediate refusal from a timeout.

The failure was measured on the catalogue's cluster (Calico) on 2026-11-12:
without its CNI file, the worker goes NotReady in under 10 s, a Pod placed on it
stays in `ContainerCreating` (`cni plugin not initialized`), and Calico does not
rewrite the file on its own. Deleting the worker's `calico-node` Pod gets it
rewritten: the node is back within 5 s.

The setup draws which of the two Services refuses and which one keeps you
waiting. The `cleanup.yaml` puts the CNI file back if it is missing, has Calico
rewrite its configuration, waits for the worker to be Ready, then removes the
namespace.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster; the failure is on `k8s-w1.lab` |
| Duration | about 30 minutes |
| Companion lesson | [Pod Networking](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pod-networking/#mettre-en-pratique) |

```bash
dsoxlab run   cka-troubleshoot-networking
dsoxlab check cka-troubleshoot-networking
```
