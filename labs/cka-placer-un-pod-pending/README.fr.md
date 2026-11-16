# Lire pourquoi quatre Pods restent en Pending et placer chacun

Lab **CKA**, domaine *Troubleshooting* (30 % de l'épreuve), compétence
« Troubleshoot clusters and nodes », et domaine *Workloads and Scheduling*,
compétence « Configure Pod admission and scheduling ».

Un Pod en Pending n'a pas d'erreur à afficher : le scheduler n'a trouvé aucun
nœud. La raison est écrite une seule fois, dans l'événement
`FailedScheduling`, au milieu du bruit de fond des nœuds écartés pour d'autres
motifs. Ce lab pose les quatre premières causes de la leçon, une par
application, et demande de les réparer sans retirer la contrainte qui bloque.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm, avec ses deux workers |
| Durée | environ 25 minutes |
| Leçon jumelée | [Diagnostiquer un Pod Pending](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/pods-pending-kubernetes/) |

```bash
dsoxlab run   cka-placer-un-pod-pending
dsoxlab check cka-placer-un-pod-pending
```
