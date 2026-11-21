# Harden a worker node and the access to the API server, without breaking the cluster

Challenge of the **Identities, access and nodes** module of the Kubernetes
course: a worker node delivered from an old server template to bring down to
what Kubernetes needs (services, SSH, sudo, kubelet, firewall), then an API
server to close to anonymous clients without breaking the health probes or
`kubeadm join`. The node is rebooted at the end to check that everything holds.
Seven requirements, pass mark 70, two blocking.

| | |
|---|---|
| Target | `k8s-cp.lab` and the optional second worker `k8s-w2.lab`, joined to the kubeadm cluster of the catalogue for the duration of the challenge |
| Duration | about 60 minutes |
| Related page | [Harden the nodes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/) (French) |

```bash
dsoxlab run    k8s-challenge-durcir-les-noeuds-et-l-acces-api
dsoxlab check  k8s-challenge-durcir-les-noeuds-et-l-acces-api
dsoxlab submit k8s-challenge-durcir-les-noeuds-et-l-acces-api
```
