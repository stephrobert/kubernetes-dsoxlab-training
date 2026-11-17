# Restreindre qui se connecte à un worker, et avec quels droits

Lab **CKS**, domaine *System Hardening* (10 % de l'épreuve), compétence
« Using least-privilege identity and access management ».

Un nœud Kubernetes est une machine Linux : qui y entre par SSH, et ce qu'il
peut y faire avec `sudo`, compte autant que le RBAC du cluster. Ce lab vous
fait réserver SSH à un groupe nommé, par clé seulement, sans vous enfermer
dehors, puis ramener un compte trop puissant à la seule commande utile.

| | |
|---|---|
| Cible | `k8s-w2.lab`, second worker du cluster kubeadm (hôte optionnel), joint depuis `k8s-cp.lab` |
| Durée | environ 25 minutes |
| Leçon jumelée | [Durcir les nœuds](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/) |

```bash
dsoxlab run   cks-restreindre-l-acces-au-noeud
dsoxlab check cks-restreindre-l-acces-au-noeud
```

Le lab monte `k8s-w2.lab` s'il ne tourne pas. Si vous vous enfermez dehors,
rien n'est perdu : `dsoxlab destroy --optional-hosts` retire la machine, et le
prochain `dsoxlab run` la remonte.
