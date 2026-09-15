# Trois Pods en CrashLoopBackOff, trois causes

Lab **CKAD**, domaine *Application Observability and Maintenance* (15 % de
l'épreuve), compétences « Utilize container logs » et « Debugging in
Kubernetes ».

Trois lectures différentes pour trois pannes : le message de sortie du
conteneur, ses logs précédents, et la raison `OOMKilled` que seul le kubelet
raconte. Chaque test observe le Pod pendant quinze secondes : un Pod
`Running` entre deux morts ne passe pas.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Diagnostiquer un CrashLoopBackOff](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/crashloopbackoff-kubernetes/) |

```bash
dsoxlab run   ckad-troubleshoot-crashloop
dsoxlab check ckad-troubleshoot-crashloop
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
