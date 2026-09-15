# Vider un worker pour une maintenance, sans couper le service

Lab **CKA**, domaine *Cluster Architecture, Installation and Configuration*
(25 % de l'épreuve), compétences « Prepare underlying infrastructure » et
« Manage the lifecycle of Kubernetes clusters ».

Le lab hérité tournait sur kind et lisait des specs : un PDB existait, des
nœuds étaient schedulables. Ici le worker est une vraie machine, le CNI y
tourne en DaemonSet, un Pod orphelin y traîne, et les tests prouvent que
chaque Pod de l'application a été recréé ailleurs après le début du lab.

| | |
|---|---|
| Cibles | `k8s-cp.lab`, et `k8s-w1.lab` joignable par `ssh` depuis le control plane |
| Durée | environ 15 minutes |
| Leçon jumelée | [Préparer une maintenance de cluster Kubernetes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/preparer-maintenance-cluster-kubernetes/) |

```bash
dsoxlab run   cka-node-drain-cordon
dsoxlab check cka-node-drain-cordon
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
