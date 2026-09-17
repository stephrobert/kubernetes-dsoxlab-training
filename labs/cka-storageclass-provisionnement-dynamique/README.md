# Get a volume nobody created, and see what becomes of it

**CKA** lab, *Storage* domain (10 % of the exam), dynamic provisioning.

Counterpart to [`cka-pv-pvc-storageclass`](../cka-pv-pvc-storageclass/), which
covers **static** provisioning, where an administrator creates the
PersistentVolume by hand. This one covers the dynamic case, and what it changes
on deletion.

**The decisive check is not that the claim is Bound**, but that the volume
belongs to the class and carries its policy. Creating a volume by hand would
bind the claim too, without any dynamic provisioning having happened: the test
does not fall for it.

The starting state rests on a distinction the documentation barely mentions:
`storageClassName: ""`, an **empty** string, **explicitly disables** dynamic
provisioning, where an **absent** field lets the default class apply. So the
claim waits for a volume nobody will create.

Measured on 2026-09-17 with Rancher's `local-path-provisioner` v0.0.33:

| | |
|---|---|
| class created | `local-path` |
| binding mode | `WaitForFirstConsumer`, so nothing binds before a Pod uses the claim |
| policy | `Delete`, the volume follows the claim |

The `cleanup.yaml` removes the provisioner, its StorageClass and its namespace,
and erases `/opt/local-path-provisioner` on the node: these are cluster-scoped
objects and files that would fill the disk over successive labs.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 25 minutes |
| Companion lesson | [StorageClass](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storageclass/) |

```bash
dsoxlab run   cka-storageclass-provisionnement-dynamique
dsoxlab check cka-storageclass-provisionnement-dynamique
```
