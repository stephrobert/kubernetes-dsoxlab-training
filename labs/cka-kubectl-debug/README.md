# Get inside a container with no shell using kubectl debug

Lab of the **Debug an application** lesson of the "Deploy your applications"
module of the Kubernetes course, and **CKA** skill of the *Troubleshooting*
domain: distroless images have neither shell nor tools, and `kubectl exec`
fails on them. An ephemeral container that shares the application's processes
lets you look inside anyway.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 10 minutes |
| Related page | [Débugger une application, Mettre en pratique section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/#mettre-en-pratique) |

```bash
dsoxlab run   cka-kubectl-debug
dsoxlab check cka-kubectl-debug
```
