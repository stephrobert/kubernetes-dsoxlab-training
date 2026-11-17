# Close the API server and the kubelet to anonymous clients without breaking kubeadm join

**CKS** lab, *Cluster Hardening* domain (15 % of the exam), competency
"Restrict access to the Kubernetes API".

Closing anonymous access seems to take a single flag, `--anonymous-auth=false`.
On a kubeadm cluster, that flag breaks `kubeadm join` discovery. This lab has
you keep anonymous access on the useful paths only, close the kubelet and bring
NodeRestriction back, without losing the ability to add a node.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster |
| Duration | about 35 minutes |
| Paired lesson | [Restreindre l'accès à l'API server](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/restreindre-acces-api-server/) (in French) |

```bash
dsoxlab run   cks-restreindre-l-acces-anonyme
dsoxlab check cks-restreindre-l-acces-anonyme
```
