# Retirer cluster-admin à un compte de service, sans le priver de son travail

Lab **CKS**, domaine *Cluster Hardening* (15 % de l'épreuve), compétences
« Use Role Based Access Controls to minimize exposure » et « Exercise caution
in using service accounts ».

Le catalogue a déjà deux labs RBAC, un CKA et un CKAD, qui apprennent à
**donner** un droit. Celui-ci apprend à en **retirer** un sans casser
l'application, ce qui est le geste du CKS et le plus difficile des deux :
personne ne se plaint d'un droit trop large tant que rien n'a fuité.

Les tests ne lisent pas les manifestes, sauf un et pour une raison précise :
un droit ne se déduit pas d'un fichier. Les règles se cumulent, un binding
oublié ailleurs peut tout rouvrir, et le nom d'un objet ne dit rien de ce
qu'il accorde. Ils posent donc les questions à l'API server avec
`kubectl auth can-i --as`, et exigent **les deux sens** : ce que le compte
doit pouvoir faire, et ce qu'il ne doit plus pouvoir faire.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [RBAC](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rbac/) |

```bash
dsoxlab run   cks-rbac-least-privilege
dsoxlab check cks-rbac-least-privilege
```

Transposé de K8sExamLab le 2026-09-16, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
