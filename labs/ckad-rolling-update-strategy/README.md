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
orphan ReplicaSet. Nine criteria then, one per asked state, each ReplicaSet
checked for its owner and its revision number.

Corrected the same day, after a campaign measured **3 tests out of 9 green
before the work**: a test that passes on the starting situation awards points
for the initial state. Eight criteria now.

- The strategy: `RollingUpdate` being Kubernetes' default, the requirement
  could never refuse. The situation changed instead, `fixtures/prepare.sh`
  now posing `type: Recreate`. The subject gains from it: the learner sees
  the difference between the two strategies.
- The five ready replicas: they were ready at the start, on the old image.
  The test now requires the complete final state, the image of the active
  revision included.
- The five asked replicas: a non-regression requirement, true before the work
  by construction. It has no criterion of its own any more, and lives as an
  assertion of the previous test.

**This rewrite has not been replayed against a cluster yet**: the 0-then-100
attestation above covers the former tests, not these.
