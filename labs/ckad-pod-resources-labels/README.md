# A two-container Pod with its resource budgets

Lab of the **Requests and Limits** lesson of the "Deploy your applications"
module of the Kubernetes course, and **CKAD** skill of the *Application Design
and Build* domain: two containers, their `resources`, and the memory limit read
in the container's cgroup, where the kernel enforces it.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Related page | [Requests et Limits, Mettre en pratique section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/#mettre-en-pratique) |

```bash
dsoxlab run   ckad-pod-resources-labels
dsoxlab check ckad-pod-resources-labels
```
