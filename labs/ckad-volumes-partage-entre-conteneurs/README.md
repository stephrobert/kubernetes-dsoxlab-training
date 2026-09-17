# Let one container read what another writes, and nothing else

**CKAD** lab, *Application Design and Build* domain (20 % of the exam),
application volumes.

Distinct from [`ckad-multi-container-sidecar`](../ckad-multi-container-sidecar/),
which covers the two-container **pattern**. This one covers what links them,
and what a container filesystem precisely does not share: two containers of the
same Pod share the network and the IP address, never their filesystem.

**The final test's second check is the one that counts.** A candidate mounting
the volume on both containers' root, or on `/tmp`, would pass the first half
without having understood what a volume shares. So the test writes a file
**outside** the volume and checks it does not cross.

The starting state is measurable before any intervention: the producer writes
every five seconds, and `ls` in the reader finds nothing.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 20 minutes |
| Companion lesson | [Application volumes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/volumes-applicatifs/) |

```bash
dsoxlab run   ckad-volumes-partage-entre-conteneurs
dsoxlab check ckad-volumes-partage-entre-conteneurs
```
