# Attach a second network interface to a Pod with Multus

Guided lab of the lesson "Give several interfaces to a Pod with Multus", level
6 "Advanced networking" of the Kubernetes course (CKNE). Let Cilium share the
CNI configuration, install Multus 4.3.2 in thick mode, describe a macvlan
network, and prove an exchange between two Pods over that second network.

| | |
|---|---|
| Target | `net-cp.lab`, the Cilium cluster without kube-proxy of the optional hosts `net-cp`, `net-w1` and `net-w2` |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (which declares Kubernetes 1.33 to 1.36), Multus v4.3.2 thick, Helm 4.3.2 |
| Duration | about 35 minutes |
| Prerequisite | the lab `k8s-installer-cilium-sans-kube-proxy` |
| Related page | [Give several interfaces to a Pod with Multus](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/multus-pod-interfaces/) |

The `run` of this lab mounts the `net-*` hosts if they are not running yet and
brings Cilium back to the values of the base cluster. The `cleanup.yaml`
deletes the namespace `multus-demo`, removes Multus with its manifest and the
files it leaves on every node (`00-multus.conf` first, which would otherwise
send every new Pod to an absent Multus), then brings Cilium back to
`cni.exclusive=true`.

```bash
dsoxlab run   k8s-attacher-une-seconde-interface
dsoxlab check k8s-attacher-une-seconde-interface
```
