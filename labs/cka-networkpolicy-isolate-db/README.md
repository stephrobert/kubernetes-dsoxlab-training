# Isolate the database: only the backend gets in

**CKA** lab, *Services and Networking* domain (20 % of the exam),
competency "Define and enforce Network Policies".

The inherited lab read the spec of the policy and attempted one connection in
each direction. Here a Pod `intrus`, with the right label but in another
namespace, must stay out: an empty `namespaceSelector`, the classic mistake,
would let it in. And the database must still be able to reach out, which a
policy that is too broad would break. Calico enforces the policies; without it,
none of this would be measurable.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Kubernetes NetworkPolicies](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |

```bash
dsoxlab run   cka-networkpolicy-isolate-db
dsoxlab check cka-networkpolicy-isolate-db
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
