# Placer avec nodeAffinity : contrainte obligatoire et préférence

Lab **CKA**, domaine *Workloads and Scheduling* (15 % de l'épreuve),
compétences de placement : `nodeAffinity` obligatoire et préférée.

Le lab hérité exigeait `kubernetes.io/os=linux`, une contrainte que tout
nœud satisfait, et ne mesurait donc rien. Ici l'obligation porte sur un
label que seul le worker a, et les trois Pods doivent y être ; le Pod
`gpu-app` doit avoir attendu son label, ce que la condition `PodScheduled`
raconte.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Scheduling avancé : Affinity, Taints, Tolerations](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/affinity-toleration-taint/) |

```bash
dsoxlab run   cka-node-affinity
dsoxlab check cka-node-affinity
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
