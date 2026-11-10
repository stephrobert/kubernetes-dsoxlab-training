# Tune a rolling update: maxSurge and maxUnavailable

**CKAD** lab, *Application Deployment* domain (20 % of the exam),
competency "Understand Deployments and how to perform rolling updates".

The inherited lab asked for an "evidence" ConfigMap copying the values
back: it proved nothing. Here each asked state is read on the cluster. The
strategy is read where it lives, on the Deployment: that, and only that,
says under which constraints the next replacement will run. The
ReplicaSets, the old one at zero and the new one complete, say something
else and narrower: that a replacement took place, through this Deployment,
and that it went all the way. They do not say it ran under the asked
constraints, and nothing can say it after the fact.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Rolling Updates and Rollbacks](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |

```bash
dsoxlab run   ckad-rolling-update-strategy
dsoxlab check ckad-rolling-update-strategy
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.

Rewritten on 2026-11-10 after an independent review: the three former tests
scored 100 on a Deployment recreated from scratch and decorated with an
orphan ReplicaSet. Nine criteria now, one per asked state, each ReplicaSet
checked for its owner and its revision number. **This rewrite has not been
replayed against a cluster yet**: the 0-then-100 attestation above covers
the former tests, not these.
