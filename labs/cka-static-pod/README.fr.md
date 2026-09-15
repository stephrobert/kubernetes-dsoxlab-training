# Poser un Pod statique sur un worker, sans passer par l'API

Lab **CKA**, domaine *Cluster Architecture, Installation and Configuration*
(25 % de l'épreuve), compétence « Understand the role of the kubelet ».

Le lab hérité de K8sExamLab n'avait pas de solution jouable, son fichier
était tronqué. Ici le candidat cherche le répertoire surveillé dans la
configuration du kubelet du worker, et le dernier test demande au runtime du
nœud s'il exécute vraiment le conteneur.

| | |
|---|---|
| Cibles | `k8s-cp.lab`, et `k8s-w1.lab` joignable par `ssh` depuis le control plane |
| Durée | environ 10 minutes |
| Leçon jumelée | [Fonctionnement des Worker Nodes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/) |

```bash
dsoxlab run   cka-static-pod
dsoxlab check cka-static-pod
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
