# Reprendre un Pod privilégié en production, sans le priver de son travail

Lab **CKS**, domaine *Minimize Microservice Vulnerabilities* (20 % de
l'épreuve), compétence « Use appropriate pod security standards », côté
remédiation.

Le catalogue a déjà `ckad-security-context-hardened`, qui apprend à
**construire** un Pod durci. Celui-ci part d'un Pod **existant**, privilégié,
qui tourne et que personne n'a signalé. Reprendre l'existant est le geste du
CKS, et il est plus difficile : il faut trouver ce qui ne va pas avant de
corriger, et le scénario ne dit pas combien de défauts il y a.

Le dernier test ne lit pas `hostPID: false` dans une spec, ce qui ne serait
qu'une absence : il **compte** les processus que le conteneur voit. Avec le
namespace de l'hôte, il énumère le kubelet, containerd et tous les conteneurs
du nœud, et peut leur envoyer des signaux.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [Pod Security Standards](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/pod-security-standards/) |

```bash
dsoxlab run   cks-secure-existing-pod
dsoxlab check cks-secure-existing-pod
```

Transposé de K8sExamLab le 2026-09-16, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
