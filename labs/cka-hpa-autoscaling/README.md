# Scale out automatically with a HorizontalPodAutoscaler

**CKA** lab, *Workloads and Scheduling* domain (15 % of the exam),
competency "Configure workload autoscaling".

The inherited lab read the spec of the HPA and a ConfigMap that copied its
values; no load was generated, no scale-up was observed. Here the tests read
the current metrics of the HPA and the `SuccessfulRescale` event that the
controller emits when it grows the Deployment: an HPA that has never rescaled
is not a validated HPA, as the lesson puts it.

metrics-server 0.9.0, the current version, is installed by the setup with the
option that kubeadm requires, and removed by the cleanup.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 20 minutes |
| Companion lesson | [Horizontal Pod Autoscaler](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/horizontal-pod-scaling/) |

```bash
dsoxlab run   cka-hpa-autoscaling
dsoxlab check cka-hpa-autoscaling
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
