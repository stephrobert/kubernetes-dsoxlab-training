# Un volume persistant : PersistentVolume, PersistentVolumeClaim et un Pod qui écrit

Lab **CKA**, domaine *Storage* (10 % de l'épreuve), compétences
« Understand persistent volumes and know how to create them », « Understand
volume modes, access modes and reclaim policies », « Understand persistent
volume claims ».

Le lab hérité lisait le fichier dans le Pod, ce qu'un `emptyDir` monté sur
`/data` aurait aussi donné. Ici le dernier test lit le même fichier sur le
disque du nœud où le Pod tourne, par ssh : c'est là que la persistance se
prouve.

| | |
|---|---|
| Cibles | `k8s-cp.lab`, et `k8s-w1.lab` joignable par `ssh` depuis le control plane |
| Durée | environ 15 minutes |
| Leçon jumelée | [Stockage Kubernetes : PV, PVC, StorageClass et CSI](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storage/) |

```bash
dsoxlab run   cka-pv-pvc-storageclass
dsoxlab check cka-pv-pvc-storageclass
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
