# Rétablir la résolution DNS du cluster

Lab **CKA**, domaine *Troubleshooting* (30 % de l'épreuve, le plus lourd des
trois examens), compétences « Troubleshoot cluster components » et
« Troubleshoot services and networking ».

Le DNS en panne est le classique de l'examen : l'application n'a rien, et
c'est un composant du cluster qu'il faut retrouver et remettre en service.

**Deux pannes, dont la seconde ne se voit qu'après la première.** CoreDNS est
à zéro réplica, et son Corefile sert la zone `cluster.locale` au lieu de
`cluster.local`. Remis à deux réplicas, CoreDNS est Running et Ready, charge
une configuration valide, et répond NXDOMAIN : il faut alors lire et restaurer
la ConfigMap. Le setup garde le Corefile d'origine sur le nœud, et le
`cleanup.yaml` le remet en place.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [CoreDNS](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/coredns/) |

```bash
dsoxlab run   cka-troubleshoot-dns
dsoxlab check cka-troubleshoot-dns
```

Transposé de K8sExamLab le 2026-09-14, puis joué : 0 avant le travail,
100 après la solution du formateur.
