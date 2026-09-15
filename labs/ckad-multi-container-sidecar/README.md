# A native sidecar that tails the application logs

**CKAD** lab, *Application Design and Build* domain (20 % of the exam),
competency "Understand multi-container Pod design patterns".

The native sidecar, an init container with `restartPolicy: Always`, has been
stable since 1.33: it is the form the exam expects, and this lab rejects the
plain second container that used to stand in for it.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Init Containers and Sidecars](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/) |

```bash
dsoxlab run   ckad-multi-container-sidecar
dsoxlab check ckad-multi-container-sidecar
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
