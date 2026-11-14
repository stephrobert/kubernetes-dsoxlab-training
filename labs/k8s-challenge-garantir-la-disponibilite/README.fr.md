# Garantir la disponibilité d'une application pendant une maintenance

Challenge du module **Fiabiliser et exploiter** de la formation Kubernetes
(niveau 4), dans la section Mettre en pratique de la leçon « Routine
d'exploitation » : une application à faire tourner en trois exemplaires
répartis sur les nœuds, avec un budget de perturbation et des sondes, qui doit
garder son minimum pendant que le check évacue lui-même le worker, puis un
rapport de routine confronté à l'état réel du cluster. Six états, seuil 70,
deux bloquants.

| | |
|---|---|
| Cibles | `k8s-cp.lab`, le cluster kubeadm du catalogue, et `k8s-w1.lab`, que le check évacue puis remet en service ; le lab pose les namespaces `paiement` et `exploitation` |
| Durée | environ 45 minutes |
| Page associée | [Routine d'exploitation](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/taches-quotidiennes-admin-kubernetes/) |

```bash
dsoxlab run    k8s-challenge-garantir-la-disponibilite
dsoxlab check  k8s-challenge-garantir-la-disponibilite
dsoxlab submit k8s-challenge-garantir-la-disponibilite
```

Le cluster du catalogue a deux nœuds ordonnançables : trois exemplaires ne
peuvent pas occuper trois nœuds différents, et le check demande autant de
nœuds que le cluster en offre. `dsoxlab clean` remet le worker en service si
un check a été interrompu pendant l'évacuation.
