# Expose an application and isolate its flows

Challenge of the **Networking and exposure** module of the Kubernetes course,
in the Put into practice section of the "Network Policies" lesson: two
applications routed by host and path, a legacy Service to repair, a client Pod
whose DNS is broken, and an isolated database that keeps its DNS egress. Seven
requirements, threshold 70, three blocking.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster (Calico, Traefik); the lab sets up the `comptoir` and `voisinage` namespaces |
| Duration | about 45 minutes |
| Related page | [Network Policies, Put into practice section](https://www.stephane-robert.info/en/docs/devsecops/runtime/network-policies/) |

```bash
dsoxlab run    k8s-challenge-exposer-et-isoler
dsoxlab check  k8s-challenge-exposer-et-isoler
dsoxlab submit k8s-challenge-exposer-et-isoler
```
