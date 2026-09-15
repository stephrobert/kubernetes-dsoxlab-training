# Confine a Pod with an AppArmor profile

**CKS** lab, *System Hardening* domain (10 % of the exam), competency
"Appropriately use kernel hardening tools such as AppArmor, seccomp".

This lab exists because the training **cannot prove it on kind**: on a
containerized node, the kubelet refuses the Pod with `Cannot enforce AppArmor:
AppArmor is not enabled on the host`. It takes a real machine, and that is
what this catalogue provides.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 25 minutes |
| Companion lesson | [AppArmor and seccomp](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/apparmor/) |

```bash
dsoxlab run   cks-apparmor-confiner-un-pod
dsoxlab check cks-apparmor-confiner-un-pod
```
