# Inject configuration and secrets into a Pod

**CKAD** lab, *Application Environment, Configuration and Security* domain
(25 % of the exam, the heaviest of the five), competencies "Understand
ConfigMaps" and "Understand Secrets".

The most frequent move of the CKAD: giving an application its configuration
without pasting it into its manifest, and its secrets without writing them
anywhere.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [ConfigMaps](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/configmaps/) |

```bash
dsoxlab run   ckad-configmap-secret-injection
dsoxlab check ckad-configmap-secret-injection
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
