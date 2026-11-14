# Read a cluster: which component does what

Challenge of the **Architecture** module of the Kubernetes course, with no
guidance, graded on the live state of the cluster (pass mark 70). It uses the
moves of the KCNA *Kubernetes Fundamentals* domain: reading Nodes, control
plane components, container runtime and events.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `architecture`, one control plane and three workers (Kubernetes 1.37) |
| Duration | about 30 minutes |
| Paired page | [Worker nodes, hands-on section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/) |

```bash
dsoxlab run   k8s-challenge-lire-un-cluster
dsoxlab check k8s-challenge-lire-un-cluster
```

It runs on a kind cluster, the tool the course teaches, with the multi-node
topology the course uses as its reference.
