# Réserver un nœud : taint, tolérance et nodeSelector

Lab **CKA**, domaine *Workloads and Scheduling* (15 % de l'épreuve),
compétences de placement : taints, tolérances, sélection par label.

Le lab hérité tournait sur kind et vérifiait qu'un Pod était « sur un
worker ». Ici le nœud est nommé, et le dernier test lit ce que le Pod
déclare : un Pod épinglé par `nodeName` arrive au même endroit en sautant le
scheduler, et le taint avec lui, ce que le test refuse.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 10 minutes |
| Leçon jumelée | [Scheduling avancé : Affinity, Taints, Tolerations](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/affinity-toleration-taint/) |

```bash
dsoxlab run   cka-taints-tolerations-placement
dsoxlab check cka-taints-tolerations-placement
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
