# Rétablir le trafic vers un Service

Lab **CKA**, domaine *Troubleshooting* (30 % de l'épreuve), compétence
« Troubleshoot services and networking ».

Trois pannes empilées, comme à l'examen : un selector qui ne trouve rien, un
port qui ne mène nulle part, et une politique réseau qui ferme tout. Le
dernier test fait une vraie requête, ce qui suppose un CNI qui applique les
NetworkPolicy : c'est pour ce lab, entre autres, que le socle est passé à
Calico.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Les Services](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/) |

```bash
dsoxlab run   cka-troubleshoot-networking
dsoxlab check cka-troubleshoot-networking
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
