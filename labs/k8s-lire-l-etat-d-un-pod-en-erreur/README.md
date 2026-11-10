# Read the state of a failing Pod

**CKAD** lab, domain *Application Observability and Maintenance*, skills
« Use built-in CLI tools to monitor Kubernetes applications » and « Utilize
container logs ».

The first reflex when a Pod will not start: read its state before touching
anything, with `get`, `describe`, `logs` and `top`.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `lab` (Kubernetes 1.37) |
| Duration | about 20 minutes |
| Paired lesson | [Read the cluster state](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-get-describe-logs-top/) (in French) |

```bash
dsoxlab run   k8s-lire-l-etat-d-un-pod-en-erreur
dsoxlab check k8s-lire-l-etat-d-un-pod-en-erreur
```

A lab of the Fundamentals module of the course, which teaches on kind: it runs
on a kind cluster, not on the catalogue's kubeadm cluster.
