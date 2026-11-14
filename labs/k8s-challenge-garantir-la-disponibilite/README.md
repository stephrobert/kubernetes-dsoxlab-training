# Keep an application available during a maintenance

Challenge of the **Make reliable and operate** module of the Kubernetes course
(level 4), in the Put into practice section of the "Operations routine"
lesson: an application to run as three copies spread across the nodes, with a
disruption budget and probes, that must keep its minimum while the check
itself evacuates the worker, then a routine report checked against the real
state of the cluster. Six states, threshold 70, two blocking.

| | |
|---|---|
| Targets | `k8s-cp.lab`, the catalogue's kubeadm cluster, and `k8s-w1.lab`, which the check evacuates then puts back into service; the lab sets up the `paiement` and `exploitation` namespaces |
| Duration | about 45 minutes |
| Related page | [Operations routine](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/taches-quotidiennes-admin-kubernetes/) (in French) |

```bash
dsoxlab run    k8s-challenge-garantir-la-disponibilite
dsoxlab check  k8s-challenge-garantir-la-disponibilite
dsoxlab submit k8s-challenge-garantir-la-disponibilite
```

The catalogue's cluster has two schedulable nodes: three copies cannot sit on
three different nodes, and the check asks for as many nodes as the cluster
offers. `dsoxlab clean` puts the worker back into service if a check was
interrupted during the evacuation.
