# Level 6 test: expose and protect a service on Cilium

End-of-level test of level 6 "Advanced networking" of the Kubernetes course
(CKNE). Expose a service over HTTPS through a Gateway served by Cilium, give
it read-only access with an L7 policy that does not cut the Gateway, encrypt
the traffic between nodes with WireGuard, and name from Hubble the request the
policy refuses. Graded on the state of the cluster, passed at 70 %, with two
blocking checks and no hint.

| | |
|---|---|
| Target | `net-cp.lab`, the Cilium cluster without kube-proxy of the optional hosts `net-cp`, `net-w1` and `net-w2` |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (which declares Kubernetes 1.33 to 1.36), Gateway API v1.6.3, Helm 4.3.2 |
| Duration | about 120 minutes |
| Prerequisite | the labs of level 6, in particular `k8s-installer-cilium-sans-kube-proxy` and `k8s-auditer-les-flux-avec-hubble` |
| Related page | [Level 6 test](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/exam-advanced-networking/) |

The `run` of this test mounts the `net-*` hosts if they are not running yet,
brings Cilium back to the values of the base cluster, removes any Gateway API
CRD, and sets the inherited state. The `cleanup.yaml` deletes the space
`boutique` and the address pools, brings Cilium back to the base values, and
only then removes the Gateway API CRDs: the other way round, Helm can no
longer read the Cilium release.

```bash
dsoxlab run   k8s-epreuve-reseau-avance
dsoxlab check k8s-epreuve-reseau-avance
```
