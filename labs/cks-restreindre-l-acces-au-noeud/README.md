# Restrict who can log into a worker node, and with what rights

**CKS** lab, *System Hardening* domain (10 % of the exam), competency "Using
least-privilege identity and access management".

A Kubernetes node is a Linux machine: who gets in through SSH, and what they
can do there with `sudo`, matters as much as the cluster RBAC. This lab has you
reserve SSH to a named group, by key only, without locking yourself out, then
cut an over-powered account down to the one useful command.

| | |
|---|---|
| Target | `k8s-w2.lab`, second worker of the kubeadm cluster (optional host), reached from `k8s-cp.lab` |
| Duration | about 25 minutes |
| Paired lesson | [Durcir les nœuds](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/) (in French) |

```bash
dsoxlab run   cks-restreindre-l-acces-au-noeud
dsoxlab check cks-restreindre-l-acces-au-noeud
```

The lab brings `k8s-w2.lab` up if it is not running. If you lock yourself out,
nothing is lost: `dsoxlab destroy --optional-hosts` removes the machine, and
the next `dsoxlab run` brings it back.
