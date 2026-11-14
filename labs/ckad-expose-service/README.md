# Expose a Deployment through a ClusterIP Service

**CKAD** lab, *Services and Networking* domain (20 % of the exam), competency
"Provide and troubleshoot access to applications via services".

The inherited lab read six specs without ever making a request. Here eleven
criteria measure one asked state each: the Deployment and the image of the Pods
it really runs, the Service with its ports, selector and ready endpoints, then
ten requests from a client. The answers are compared to the REAL list of Pods,
and each Pod is queried on its own loopback: a container serving an invented
identifier is refused.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 10 minutes |
| Companion lesson | [Services](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/services/) |

```bash
dsoxlab run   ckad-expose-service
dsoxlab check ckad-expose-service
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
