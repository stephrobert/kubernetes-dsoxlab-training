# Find, count and log refused flows with Hubble

Challenge of the Kubernetes training, in the Put it into practice section of
the "Hubble" lesson: find the flow an egress policy refuses and the node that
sees it, make the drop metric name its source and destination, and log the
refusals of one namespace only. Three requirements, pass mark 70%, two of
them blocking.

| | |
|---|---|
| Target | `net-cp.lab`, control plane of the Cilium cluster without kube-proxy, with `net-w1.lab` and `net-w2.lab` |
| Duration | about 45 minutes |
| Related page | [Hubble, Put it into practice section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/hubble/#mettre-en-pratique) (French only) |

```bash
dsoxlab run    k8s-challenge-retrouver-les-flux-refuses
dsoxlab check  k8s-challenge-retrouver-les-flux-refuses
dsoxlab submit k8s-challenge-retrouver-les-flux-refuses
```
