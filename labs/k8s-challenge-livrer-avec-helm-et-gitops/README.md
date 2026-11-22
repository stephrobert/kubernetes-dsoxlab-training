# Ship an application with Helm and GitOps, from a built image

Challenge of the **Package and ship** module of the Kubernetes course: an
image to build and push to the cluster registry, a Helm release installed from
a values file and pinned by digest, an upgrade followed by a rollback, and a
Git repository that Argo CD must follow until it is synchronised. Six
requirements, pass mark 70, two blocking.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `lab`; the lab installs Argo CD, a local registry and a Git repository, and puts the work in `~/livraison/` |
| Duration | about 60 minutes |
| Related page | [GitOps](https://www.stephane-robert.info/en/docs/devsecops/delivery/gitops/) |

```bash
dsoxlab run    k8s-challenge-livrer-avec-helm-et-gitops
dsoxlab check  k8s-challenge-livrer-avec-helm-et-gitops
dsoxlab submit k8s-challenge-livrer-avec-helm-et-gitops
```
