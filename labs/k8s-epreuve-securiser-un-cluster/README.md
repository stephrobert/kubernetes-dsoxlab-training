# Level 5 test: secure a cluster

End-of-level test of the Kubernetes course: from a weak inherited state and
requirements that name no Kubernetes object, secure the cluster hosting the
shop. Control plane, audit log, admission, confinement, network, detection
with Falco and supply chain, while the shop keeps answering. Graded on the
final state: nineteen states of equal weight, pass mark 70, seven critical
states, paid hints.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab installs Falco 0.45.2, Istio 1.31, gVisor, trivy, cosign and crane, a local registry, and sets up the `boutique`, `coffre`, `commandes`, `exterieur`, `paiement`, `registre` and `conformite` spaces |
| Duration | about 150 minutes |
| Related page | [Level 5 exam: secure a cluster](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/exam-secure-a-cluster/) |

```bash
dsoxlab run    k8s-epreuve-securiser-un-cluster
dsoxlab check  k8s-epreuve-securiser-un-cluster
dsoxlab submit k8s-epreuve-securiser-un-cluster
```
