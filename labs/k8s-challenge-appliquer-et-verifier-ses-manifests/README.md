# Apply and check your manifests, from a set of requirements

Challenge of the **Write and apply your manifests** module of the Kubernetes
course: an application to write from requirements that never name the
objects, shipped in two variants from one Kustomize base, with an API field to
find, a diff before the upgrade and a delivery that waits for availability. Six
requirements, pass mark 70, two blocking.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `lab`; the lab puts the requirements in `~/annuaire/` |
| Duration | about 45 minutes |
| Related page | [Kustomize](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kustomize/) |

```bash
dsoxlab run    k8s-challenge-appliquer-et-verifier-ses-manifests
dsoxlab check  k8s-challenge-appliquer-et-verifier-ses-manifests
dsoxlab submit k8s-challenge-appliquer-et-verifier-ses-manifests
```
