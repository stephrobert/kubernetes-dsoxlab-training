# Partition three tiers with ingress and egress NetworkPolicy

**CKAD** lab, *Services and Networking* domain (20 % of the exam), competency
"Demonstrate basic understanding of NetworkPolicies".

The inherited lab read eight specs without ever attempting a connection. Here
every rule is measured by a real request, the one that goes through and the
one that is blocked: this lab is one of the reasons the shared base moved to
Calico.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 20 minutes |
| Companion lesson | [Network Policies](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |

```bash
dsoxlab run   ckad-networkpolicy-ingress-egress
dsoxlab check ckad-networkpolicy-ingress-egress
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
