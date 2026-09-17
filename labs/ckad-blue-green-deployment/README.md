# Switch traffic from one version to the other: blue-green

**CKAD** lab, *Application Deployment* domain (20 % of the exam), competency
"Use Kubernetes primitives to implement common deployment strategies
(blue/green or canary)".

The inherited lab checked the Service selector without ever making a request.
Here each version answers with its own name, and six requests from a client
must all answer `green`.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Rolling updates and rollbacks](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |

```bash
dsoxlab run   ckad-blue-green-deployment
dsoxlab check ckad-blue-green-deployment
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
