# Use a custom resource, read its schema refusals, unblock it

Guided lab of the "Operators and CRDs for developers" lesson of the **Advanced
workloads** module of the Kubernetes course: discover the API group of a CRD,
create and modify custom resources, read the refusal of the API for an
out-of-bounds value, and unblock a resource stuck in Terminating.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `lab`; the lab sets up the `Sauvegarde` CRD and the `sauvegardes` namespace |
| Duration | about 25 minutes |
| Related page | [Operators et CRDs pour développeurs, Mettre en pratique section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/operators-crds-developpeurs/) |

```bash
dsoxlab run   ckad-crd-ressource-personnalisee
dsoxlab check ckad-crd-ressource-personnalisee
```
