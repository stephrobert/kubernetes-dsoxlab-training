# Keep data beyond the life of a Pod

Challenge of the **Persistent storage** module of the Kubernetes course, in the
Mettre en pratique section of the "StorageClass" lesson: a claim served by a
StorageClass, a witness file that survives its Pod, a reclaim policy, and a
Pending claim to diagnose before fixing it. Six requirements, pass mark 70,
three blocking.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `lab`; the lab sets up the `archives` namespace and a Pending claim |
| Duration | about 40 minutes |
| Related page | [StorageClass, Mettre en pratique section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/storageclass/) |

```bash
dsoxlab run    k8s-challenge-donnees-qui-survivent
dsoxlab check  k8s-challenge-donnees-qui-survivent
dsoxlab submit k8s-challenge-donnees-qui-survivent
```
