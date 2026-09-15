# Un agent sur chaque nœud, control plane compris

Lab **CKA**, domaine *Workloads and Scheduling* (15 % de l'épreuve),
compétence « Understand the primitives used to create robust, self-healing,
application deployments », ici le DaemonSet et les tolérances.

Le socle du catalogue retire le taint du control plane pour laisser de la
place aux labs à un nœud. Ce lab le remet, le temps de la session, et les
tests exigent qu'il y reste : l'agent doit y tourner par une tolérance, pas
parce que le control plane a été ouvert à tous.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 10 minutes |
| Leçon jumelée | [DaemonSets Kubernetes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/daemonsets/) |

```bash
dsoxlab run   cka-daemonset-all-nodes
dsoxlab check cka-daemonset-all-nodes
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
