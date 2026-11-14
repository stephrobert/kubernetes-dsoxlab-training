# Read the CRI, CNI and CSI interfaces of a node

Guided lab of the "CNI, CSI and CRI" lesson, Install a cluster module of level
4: on a kubeadm node, read the runtime socket the kubelet uses, the runtime
reported to the API, the CNI configuration in force and the cluster's CSI
drivers. Each answer is compared with the real value, read on the node.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster |
| Duration | about 20 minutes |
| Related page | [CNI, CSI and CRI, Put into practice section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cni-csi-cri/#mettre-en-pratique) (in French) |

```bash
dsoxlab run   k8s-lire-les-interfaces-d-un-noeud
dsoxlab check k8s-lire-les-interfaces-d-un-noeud
```
