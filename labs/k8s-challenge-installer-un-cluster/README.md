# Install a kubeadm cluster, join a node and make the control plane highly available

Challenge of the **Install a cluster** module of the Kubernetes course (level
4), in the Put into practice section of the "High availability" lesson: a reset
worker to prepare and join to the kubeadm cluster so that it survives a
reboot, a Pod forced onto it, then a kind cluster with three control planes
behind its load balancer, which must survive the loss of one of them. Seven
states, threshold 70, two blocking.

The high availability states run on kind because the catalogue's
infrastructure carries a single kubeadm control plane: kind sets up the load
balancer itself, and its nodes are kubeadm machines with stacked etcd. The
setup deletes the other labs' kind clusters to free memory; each one recreates
its own through its setup.

| | |
|---|---|
| Target | `k8s-cp.lab` and `k8s-w1.lab`, the catalogue's kubeadm cluster; `k8s-kind.lab`, where the learner creates cluster `ha` |
| Duration | about 60 minutes |
| Related page | [High availability](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ha-control-plane/) |

```bash
dsoxlab run    k8s-challenge-installer-un-cluster
dsoxlab check  k8s-challenge-installer-un-cluster
dsoxlab submit k8s-challenge-installer-un-cluster
```
