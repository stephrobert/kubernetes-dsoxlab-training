# Ramener un nœud NotReady dans le cluster

Lab **CKA**, domaine *Troubleshooting* (30 % de l'épreuve), compétence
« Troubleshoot clusters and nodes ».

Ce lab existe parce que la formation **ne peut pas le prouver sur kind** : le
kubelet est un service systemd d'une vraie machine, et il faut un second nœud
pour en casser un sans casser l'API. C'est le premier lab du catalogue qui
emploie le worker `k8s-w1.lab`.

| | |
|---|---|
| Cibles | `k8s-cp.lab`, et `k8s-w1.lab` joignable par `ssh` depuis le control plane |
| Durée | environ 15 minutes |
| Leçon jumelée | [Diagnostiquer une panne du cluster](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/) |

```bash
dsoxlab run   cka-troubleshoot-node-notready
dsoxlab check cka-troubleshoot-node-notready
```

Transposé de K8sExamLab le 2026-09-14, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
