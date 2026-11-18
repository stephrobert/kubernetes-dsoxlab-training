# Serve a Gateway and filter at L7 with Cilium

Guided lab of the lesson "Serve a Gateway and filter at L7 with Cilium", level
6 "Advanced networking" of the Kubernetes course (CKNE). Turn on Cilium's
Gateway API, serve an application through a Gateway, and give it read-only
access with an L7 policy that does not cut the Gateway.

| | |
|---|---|
| Target | `net-cp.lab`, the Cilium cluster without kube-proxy of the optional hosts `net-cp`, `net-w1` and `net-w2` |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (which declares Kubernetes 1.33 to 1.36), Gateway API v1.6.3, Helm 4.3.2 |
| Duration | about 35 minutes |
| Prerequisite | the lab `k8s-installer-cilium-sans-kube-proxy` |
| Related page | [Serve a Gateway and filter at L7 with Cilium](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/cilium-gateway-l7/) |

The `run` of this lab mounts the `net-*` hosts if they are not running yet,
brings Cilium back to the values of the base cluster and removes any Gateway
API CRD. The `cleanup.yaml` deletes the namespace `catalogue` and the address
pools, brings Cilium back to the base values, and only then removes the
Gateway API CRDs: the other way round, Helm can no longer read the Cilium
release.

```bash
dsoxlab run   k8s-filtrer-en-l7-avec-cilium
dsoxlab check k8s-filtrer-en-l7-avec-cilium
```
