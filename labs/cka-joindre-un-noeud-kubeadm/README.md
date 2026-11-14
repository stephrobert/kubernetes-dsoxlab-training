# Join a worker to a kubeadm cluster

Guided lab of the lesson « Join a node », module Install a cluster of level 4:
prepare a reset worker (swap, containerd's cgroup driver, held packages), join
it with the control plane's command, check that it is Ready with the right
kubelet, then run a Pod on it. The cleanup gives the worker back to the
cluster, whatever state is left.

| | |
|---|---|
| Target | `k8s-cp.lab` and `k8s-w1.lab`, the catalogue's kubeadm cluster |
| Duration | about 30 minutes |
| Companion lesson | [Join a node, Practice section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubeadm-join-a-node/) |

```bash
dsoxlab run   cka-joindre-un-noeud-kubeadm
dsoxlab check cka-joindre-un-noeud-kubeadm
```
