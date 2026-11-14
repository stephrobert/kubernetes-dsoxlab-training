# Ship the storefront and bring the stock service back

Challenge of the **Fundamentals** module of the Kubernetes course, with no
guidance, graded on the final state (pass mark 70, two blocking requirements).
It uses the moves of the KCNA *Kubernetes Fundamentals* domain (Kubernetes Core
Concepts) and the setup of the `kubectl` client.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `boutique` (Kubernetes 1.37) |
| Duration | about 30 minutes |
| Paired page | [Module knowledge check](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/fundamentals/knowledge-check/) |

```bash
dsoxlab run   k8s-challenge-premier-deploiement
dsoxlab check k8s-challenge-premier-deploiement
```

It runs on a kind cluster, the tool the course teaches, not on the
catalogue's kubeadm cluster.
