# Remove from a worker node what listens without serving Kubernetes

**CKS** lab, *System Hardening* domain (10 % of the exam), competency
"Minimize host OS footprint (reduce attack surface)".

A Kubernetes node needs only a handful of ports and services. Everything else
widens the attack surface and brings nothing. This lab has you tie each open
port to its source, then remove for good what does not serve, without taking
the node out of the cluster.

| | |
|---|---|
| Target | `k8s-w2.lab`, second worker of the kubeadm cluster (optional host), reached from `k8s-cp.lab` |
| Duration | about 20 minutes |
| Paired lesson | [Durcir les nœuds](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/) (in French) |

```bash
dsoxlab run   cks-reduire-la-surface-du-noeud
dsoxlab check cks-reduire-la-surface-du-noeud
```

The lab brings `k8s-w2.lab` up if it is not running. If you remove an
essential package by mistake, `dsoxlab destroy --optional-hosts` removes the
machine, and the next `dsoxlab run` brings it back.
