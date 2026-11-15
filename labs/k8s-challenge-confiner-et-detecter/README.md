# Confine a Pod and detect abnormal activity, without guidance

Challenge of the **Confine and detect** module of the Kubernetes course, in
the Put into practice section of the "Runtime Sandboxes (gVisor, Kata)"
lesson: an AppArmor profile to write and load, a seccomp profile that refuses
`chmod`, mutual TLS to require in an Istio mesh, a namespace to close by
default without cutting its application flow or its DNS, a Pod to run in a
gVisor sandbox, and a Falco rule that raises an alert for a shell in the
protected namespace, and nowhere else. Sixteen states, threshold 70, three
blocking.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab installs Falco 0.45.2 (modern eBPF driver), Istio 1.31 and gVisor, and sets up the `coffre`, `maille`, `exterieur` and `donnees` namespaces |
| Duration | about 75 minutes |
| Related page | [Runtime Sandboxes, Put into practice section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/runtime-sandboxes/) |

```bash
dsoxlab run    k8s-challenge-confiner-et-detecter
dsoxlab check  k8s-challenge-confiner-et-detecter
dsoxlab submit k8s-challenge-confiner-et-detecter
```
