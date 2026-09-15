# A persistent volume: PersistentVolume, PersistentVolumeClaim and a Pod that writes

**CKA** lab, *Storage* domain (10 % of the exam), competencies
"Understand persistent volumes and know how to create them", "Understand
volume modes, access modes and reclaim policies", "Understand persistent
volume claims".

The lab inherited from K8sExamLab read the file inside the Pod, which an
`emptyDir` mounted on `/data` would also have given. Here the last test
reads the same file on the disk of the node where the Pod runs, over ssh:
that is where persistence is proven.

| | |
|---|---|
| Targets | `k8s-cp.lab`, and `k8s-w1.lab` reachable over `ssh` from the control plane |
| Duration | about 15 minutes |
| Companion lesson | [Kubernetes storage: PV, PVC, StorageClass and CSI](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storage/) |

```bash
dsoxlab run   cka-pv-pvc-storageclass
dsoxlab check cka-pv-pvc-storageclass
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
