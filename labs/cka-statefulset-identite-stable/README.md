# Give each replica a stable identity with a StatefulSet

Guided lab of the "StatefulSets" lesson of the **Advanced workloads** module of
the Kubernetes course: replace a Deployment without identity with a StatefulSet
behind a headless Service, with one volume per replica, and prove that data
survives its Pod.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `lab`; the lab sets up the annuaire as a Deployment in the `identites` namespace |
| Duration | about 30 minutes |
| Related page | [Les StatefulSets, Mettre en pratique section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/statefulsets/) |

```bash
dsoxlab run   cka-statefulset-identite-stable
dsoxlab check cka-statefulset-identite-stable
```
