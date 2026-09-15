# Attendre une dépendance avec un init container

Lab **CKAD**, domaine *Application Design and Build* (20 % de l'épreuve),
compétence « Understand multi-container Pod design patterns ».

Le lab hérité faisait attendre « que le Service soit résolvable par DNS » :
un Service se résout dès qu'il existe, même sans endpoint, et ce gardien
n'aurait rien attendu. Ici il attend une réponse HTTP, et le Pod reste
vraiment en `Init` tant que rien ne répond.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Init Containers et Sidecars](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/) |

```bash
dsoxlab run   ckad-init-container
dsoxlab check ckad-init-container
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
