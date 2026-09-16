# Refuser un Pod privilégié à l'admission, avec Pod Security Admission

Lab **CKS**, domaine *Minimize Microservice Vulnerabilities* (20 % de
l'épreuve), compétence « Use appropriate pod security standards ».

C'est le contrôle qui a remplacé PodSecurityPolicy, retiré en 1.25. Il est
intégré à l'API server : aucun composant à installer, ce qui en fait le
premier lab CKS à écrire après AppArmor.

Le dernier test est le seul qui prouve quelque chose. Lire les labels d'un
namespace montre qu'ils sont posés, pas que l'admission les applique. Il
soumet donc deux vrais Pods à l'API server, l'un interdit et l'autre conforme,
en **dry-run côté serveur** : le verdict est réel, et rien n'est écrit.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Pod Security Standards](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/pod-security-standards/) |

```bash
dsoxlab run   cks-pod-security-admission
dsoxlab check cks-pod-security-admission
```

Le Pod `laxiste`, créé par le setup avant toute activation, continue de
tourner une fois le standard posé. Ce n'est pas un oubli : l'admission agit
sur les demandes, jamais rétroactivement, et c'est ce que les candidats
découvrent le plus souvent le jour de l'examen.

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
