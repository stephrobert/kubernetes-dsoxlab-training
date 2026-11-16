# Make the health of a cluster readable and write its health report

**CKA** lab, *Troubleshooting* domain, competency "Monitor cluster and
application resource usage".

Without metrics-server, `kubectl top` stays silent, and it is easy to mix up
what a node uses with what it has reserved. This lab has you install
metrics-server on a kubeadm cluster, then read both measures to write a health
report.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster |
| Duration | about 25 minutes |
| Lesson | [Observer la santé d'un cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/observer-sante-cluster-kubernetes/) (French) |

```bash
dsoxlab run   k8s-observer-la-sante-d-un-cluster
dsoxlab check k8s-observer-la-sante-d-un-cluster
```
