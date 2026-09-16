# Forbid everything, then reopen the strict minimum, DNS included

**CKS** lab, *Cluster Setup* domain (15 % of the exam), competency "Use
Network security policies to restrict cluster level access".

The catalogue already has two NetworkPolicy labs, one CKA and one CKAD, which
teach how to **allow** a flow. This one starts from the opposite, the
zero-trust model: close everything, then reopen. The trap it exercises only
exists that way round, and it is the costliest of the domain: **a
default-closed egress breaks DNS**, and nothing signals it, neither in the
events nor in the Pod status.

The Pods are provided by the setup. That is not a shortcut: the CKS subject is
closing a namespace without breaking what must keep running, not creating
Pods. `annuaire` is the measuring instrument for egress, and it really
listens: a request to a Pod that listens to nothing fails anyway, and a test
built on such a target would be true before the work.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 20 minutes |
| Companion lesson | [Network Policies](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |

```bash
dsoxlab run   cks-networkpolicy-default-deny
dsoxlab check cks-networkpolicy-default-deny
```

Ported from K8sExamLab on 2026-09-16, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
