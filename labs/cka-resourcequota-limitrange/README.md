# Cap a namespace without blocking those who forget to declare

**CKA** and **CKAD** lab, *Workloads and Scheduling* domain (15 % of the CKA)
and *Application Environment* on the CKAD side.

**The two objects go together, and that is the whole subject.** Creating the cap
alone turns a developer's oversight into an incomprehensible refusal: as soon as
a quota applies to `requests`, a Pod declaring none becomes invalid, the API
being unable to count what is not declared. The lab makes that dependency felt
rather than stated.

**Both tests are active proofs**, and opposite ones:

| probe | expected | why |
|---|---|---|
| a Pod requesting 64 CPU | **refused at creation** | without a quota the API accepts it and it stays Pending: nobody refused it |
| a Pod with no resources at all | **accepted, then completed** | without defaults, the quota itself would refuse it |

Re-reading the objects would prove nothing: a ResourceQuota whose `hard` does
not apply to the right resources is perfectly valid and caps nothing; a
LimitRange whose `type` is wrong completes no container.

The last check verifies the namespace's application still runs: too low a cap
would keep it from being scheduled again, and that would be an outage.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 25 minutes |
| Companion lesson | [ResourceQuota and LimitRange](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/resource-quotas/) |

```bash
dsoxlab run   cka-resourcequota-limitrange
dsoxlab check cka-resourcequota-limitrange
```
