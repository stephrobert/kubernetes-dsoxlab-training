# Réparer un kubelet qui refuse de démarrer

Lab **CKA**, domaine *Troubleshooting* (30 % de l'épreuve), compétences
« Troubleshoot clusters and nodes » et « Troubleshoot cluster components ».

Ce lab existe parce que la formation **ne peut pas le prouver sur kind** : un
kubelet est un service systemd, son journal est celui d'une vraie machine, et
sa configuration est celle que `kubeadm` a écrite. La vague 1 du backlog le
réclamait sous le nom `cka-reparer-un-kubelet`.

| | |
|---|---|
| Cibles | `k8s-cp.lab`, et `k8s-w1.lab` joignable par `ssh` depuis le control plane |
| Durée | environ 15 minutes |
| Leçon jumelée | [Diagnostiquer une panne du cluster](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/) |

```bash
dsoxlab run   cka-troubleshoot-kubelet
dsoxlab check cka-troubleshoot-kubelet
```

Transposé de K8sExamLab le 2026-09-14, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
