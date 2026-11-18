# Announce Pods and Services to a router with BGP

Guided lab of the lesson "Announce Services with BGP", level 6 "Advanced
networking" of the Kubernetes course (CKNE). Turn on the Cilium BGP control
plane, peer the three nodes with an external FRR router, announce the Pod
networks and a LoadBalancer address, and reach the Service from the router.

| | |
|---|---|
| Target | `net-cp.lab`, the Cilium cluster without kube-proxy of the optional hosts `net-cp`, `net-w1` and `net-w2`; the FRR router runs on `k8s-cp.lab`, outside that cluster |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (which declares Kubernetes 1.33 to 1.36), FRR 10.6.2, Helm 4.3.2 |
| Duration | about 40 minutes |
| Prerequisite | the lab `k8s-installer-cilium-sans-kube-proxy` |
| Related page | [Announce Services with BGP](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/announce-services-bgp/) |

The `run` of this lab mounts the `net-*` hosts if they are not running yet,
brings Cilium back to the values of the base cluster, and starts the FRR
router on `k8s-cp.lab`: a container started by `ctr`, in a network namespace
of its own with a macvlan interface at `10.10.50.200`, inside a transient
systemd unit. The `cleanup.yaml` deletes the BGP resources, the address pool
and the namespace `bgp-demo`, removes the `bgp` label from the nodes, brings
Cilium back to the base values, and removes the router with its namespace.

```bash
dsoxlab run   k8s-annoncer-un-service-en-bgp
dsoxlab check k8s-annoncer-un-service-en-bgp
```
