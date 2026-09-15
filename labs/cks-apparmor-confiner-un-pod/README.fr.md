# Confiner un Pod avec un profil AppArmor

Lab **CKS**, domaine *System Hardening* (10 % de l'épreuve), compétence
« Appropriately use kernel hardening tools such as AppArmor, seccomp ».

Ce lab existe parce que la formation **ne peut pas le prouver sur kind** : sur
un nœud en conteneur, le kubelet refuse le Pod avec `Cannot enforce AppArmor:
AppArmor is not enabled on the host`. Il faut une vraie machine, et c'est ce
que ce catalogue fournit.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 25 minutes |
| Leçon jumelée | [AppArmor et seccomp](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/apparmor/) |

```bash
dsoxlab run   cks-apparmor-confiner-un-pod
dsoxlab check cks-apparmor-confiner-un-pod
```
