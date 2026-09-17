# Interdire un appel système à un conteneur, et le prouver de l'intérieur

Lab **CKS**, domaine *System Hardening* (10 % de l'épreuve), compétence
« Minimize host OS footprint (reduce attack surface) ».

C'est le jumeau de `cks-apparmor-confiner-un-pod`, et il obéit à la même
règle du dépôt : vérifier qu'un profil est chargé et qu'un Pod le déclare **ne
prouve pas** que le confinement agit, un profil vide passerait. Le dernier
test exerce donc les deux côtés, dans le conteneur : `chmod` doit échouer avec
`EPERM`, et créer un fichier doit toujours marcher.

Un quatrième test interroge le Pod témoin, qui ne déclare aucun profil : c'est
ce qui distingue un filtre posé sur le bon Pod d'un durcissement global du
nœud, lequel répondrait à côté et casserait tout ce qui tourne dessus.

Le profil vit sur le **nœud**, pas dans le cluster : c'est la même raison
d'être des VM que pour AppArmor.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 25 minutes |
| Leçon jumelée | [Seccomp](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/seccomp/) |

```bash
dsoxlab run   cks-seccomp-profile
dsoxlab check cks-seccomp-profile
```

Le `cleanup.yaml` retire le profil du disque du nœud. Sans cela, le prochain
passage trouverait un profil déjà en place et le premier test passerait avant
tout travail, sans que le validateur le voie : il photographie le cluster, pas
le disque.

Transposé de K8sExamLab le 2026-09-16, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
