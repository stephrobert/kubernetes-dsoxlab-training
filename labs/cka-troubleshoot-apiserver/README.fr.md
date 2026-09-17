# Remettre l'API server en service

Lab **CKA**, domaine *Troubleshooting* (30 % de l'épreuve), compétence
« Troubleshoot cluster components ».

Ce lab existe parce que la formation **ne peut pas le prouver sur kind** : le
manifeste statique, le kubelet qui le relit et le runtime qui garde les
journaux du conteneur mort sont ceux d'une vraie machine. Sans API, il faut
savoir se passer de `kubectl`.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm |
| Durée | environ 15 minutes |
| Leçon jumelée | [Control Plane Kubernetes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/control-plan/) |

```bash
dsoxlab run   cka-troubleshoot-apiserver
dsoxlab check cka-troubleshoot-apiserver
```

Transposé de K8sExamLab le 2026-09-14, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
