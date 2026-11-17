# Close a worker node to the network, except the flows Kubernetes needs

**CKS** lab, *System Hardening* domain (10 % of the exam), competency
"Minimize external access to the network".

A host firewall on a Kubernetes node must close the rest without cutting the
kubelet, the network plugin or administration, and without erasing the rules
that kube-proxy and Calico write themselves. This lab has you write that chain,
load it without locking yourself out, and make it survive a reboot.

| | |
|---|---|
| Target | `k8s-w2.lab`, second worker of the kubeadm cluster (optional host), reached from `k8s-cp.lab` |
| Duration | about 35 minutes |
| Paired lesson | [Durcir les nœuds](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/) (in French) |

```bash
dsoxlab run   cks-fermer-l-acces-reseau-au-noeud
dsoxlab check cks-fermer-l-acces-reseau-au-noeud
```

The check reboots `k8s-w2.lab`: count two more minutes.
