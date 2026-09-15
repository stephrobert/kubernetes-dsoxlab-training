# Harden a Pod with a securityContext

**CKAD** lab, *Application Environment, Configuration and Security* domain
(25 % of the exam), competency "Understand SecurityContexts".

Hardening a Pod is easy; keeping it running once hardened is less so. This
lab requires both: the confinement holds, and the application serves.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Security Context](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/) |

```bash
dsoxlab run   ckad-security-context-hardened
dsoxlab check ckad-security-context-hardened
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
