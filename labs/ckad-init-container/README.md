# Wait for a dependency with an init container

**CKAD** lab, *Application Design and Build* domain (20 % of the exam),
competency "Understand multi-container Pod design patterns".

The inherited lab waited "for the Service to be resolvable through DNS": a
Service resolves as soon as it exists, even with no endpoint, so that guard
would have waited for nothing. Here it waits for an HTTP answer, and the Pod
really stays in `Init` as long as nothing answers.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Init Containers and Sidecars](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/) |

```bash
dsoxlab run   ckad-init-container
dsoxlab check ckad-init-container
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
