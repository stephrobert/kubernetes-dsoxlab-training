# Detect and contain a persistence and a denial of service

Challenge of the **Threat model and frameworks** module of the Kubernetes
course (level 5, KCSA), in the Put into practice section of the "Denial of
service" lesson: an attacker's access that something keeps recreating, to
record and remove for good without harming the legitimate application, then an
abusive workload to contain in its namespace while another application keeps
answering. Seven states, threshold 70, two blocking.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab sets up the `reservations` and `calcul-lots` namespaces and three cluster-wide objects of the attacker |
| Duration | about 45 minutes |
| Related page | [Kubernetes course](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/), until the lesson is published |

The persistence differs from the guided lab `k8s-detecter-une-persistance`,
and so do the names: play the two guided labs of the module first.

The abusive workload is safe for the shared node by construction: a fixed
64 MiB block per Pod in a memory-backed `emptyDir`, and one processor busy
half of the time.

```bash
dsoxlab run    k8s-challenge-contenir-une-attaque
dsoxlab check  k8s-challenge-contenir-une-attaque
dsoxlab submit k8s-challenge-contenir-une-attaque
```
