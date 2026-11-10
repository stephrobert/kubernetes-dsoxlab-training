# Switch traffic from one version to the other: blue-green

**CKAD** lab, *Application Deployment* domain (20 % of the exam), competency
"Use Kubernetes primitives to implement common deployment strategies
(blue/green or canary)".

The inherited lab checked the Service selector without ever making a request.
The first rewrite made six requests through the Service, but never queried the
blue version: `app-blue` could be a `sleep 3600` with no server at all and the
lab still returned 100. Since the rewrite of 2026-11-10, each Pod of each
version is queried **on its own address**, so blue has to stay standing and
serving, which is the only reason a blue-green rollback is instant.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Rolling updates and rollbacks](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |

Ten criteria, one per state the statement asks for: two Deployments (replicas,
labels, served version), the Service (port, selector, endpoints), and the six
requests from the client.

```bash
dsoxlab run   ckad-blue-green-deployment
dsoxlab check ckad-blue-green-deployment
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace. **The rewrite of 2026-11-10 has
not been replayed on a cluster yet**: a campaign was running on the
catalogue, so the cycle has to be played again before this lab can be
declared attested.
