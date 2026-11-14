# Create your StorageClass and get a volume no administrator created

**CKA** lab, *Storage* domain (10 % of the exam), StorageClass and dynamic
provisioning.

Counterpart to [`cka-pv-pvc-storageclass`](../cka-pv-pvc-storageclass/), which
covers **static** provisioning, where an administrator creates the
PersistentVolume by hand. This one covers the dynamic case: the learner
**creates their own StorageClass**, `garde`, which reuses the provisioner
already installed with another policy, then gets a volume from it on demand.

**The decisive check is not that the claim is Bound**, but that the volume was
created for it by the provisioner, and carries the policy of `garde`. Creating a
volume by hand would bind the claim too: the test does not fall for it. Neither
does renaming `local-path` to `garde`: the original class must stay in place.

The starting state rests on a distinction the documentation barely mentions:
`storageClassName: ""`, an **empty** string, **explicitly disables** dynamic
provisioning, where an **absent** field lets the default class apply.

The provisioner is Rancher's `local-path-provisioner` v0.0.37, images pinned by
digest:

| | `local-path` (installed) | `garde` (to create) |
|---|---|---|
| provisioner | `rancher.io/local-path` | the same |
| binding mode | `WaitForFirstConsumer` | `WaitForFirstConsumer` |
| policy | `Delete`, the volume follows the claim | `Retain`, the volume stays |

The `cleanup.yaml` removes the namespace, the volumes `Retain` kept, the `garde`
class, the provisioner and its namespace, and erases `/opt/local-path-provisioner`
on the node.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 30 minutes |
| Companion lesson | [StorageClass](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/storageclass/) |

```bash
dsoxlab run   cka-storageclass-provisionnement-dynamique
dsoxlab check cka-storageclass-provisionnement-dynamique
```
