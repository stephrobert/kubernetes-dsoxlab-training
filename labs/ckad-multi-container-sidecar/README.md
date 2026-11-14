# A native sidecar that tails the application logs

**CKAD** lab, *Application Design and Build* domain (20 % of the exam),
competency "Understand multi-container Pod design patterns".

The native sidecar, an init container with `restartPolicy: Always`, is the
form the exam expects, and this lab rejects a plain second container.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Init Containers and Sidecars](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/init-containers-and-sidecars/) |

```bash
dsoxlab run   ckad-multi-container-sidecar
dsoxlab check ckad-multi-container-sidecar
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
