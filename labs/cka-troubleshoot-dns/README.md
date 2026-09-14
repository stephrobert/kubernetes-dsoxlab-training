# Rétablir la résolution DNS du cluster

Lab **CKA**, domaine *Troubleshooting* (30 % de l'épreuve, le plus lourd des
trois examens), compétences « Troubleshoot cluster components » et
« Troubleshoot services and networking ».

Le DNS en panne est le classique de l'examen : l'application n'a rien, et
c'est un composant du cluster qu'il faut retrouver et remettre en service.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 10 minutes |
| Leçon jumelée | [CoreDNS](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/coredns/) |

```bash
dsoxlab run   cka-troubleshoot-dns
dsoxlab check cka-troubleshoot-dns
```

Transposé de K8sExamLab le 2026-09-14, puis joué : 0 avant le travail,
100 après la solution du formateur.
