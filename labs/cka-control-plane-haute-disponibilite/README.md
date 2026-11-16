# Build a kubeadm control plane with three nodes behind a load balancer, and lose one

**CKA** lab, *Cluster Architecture, Installation and Configuration* domain,
competency "Implement and configure a highly-available control plane".

A single control plane is a single point of failure. This lab has you build,
with kubeadm, three stacked-etcd control planes behind an HAProxy load
balancer, then proves high availability by stopping one of them.

| | |
|---|---|
| Targets | `ha-cp1.lab`, `ha-cp2.lab`, `ha-cp3.lab` and the load balancer `ha-lb.lab`, optional hosts started for this lab only |
| Duration | about 40 minutes |
| Lesson | [Kubernetes High Availability: the Control Plane](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/ha-control-plane/) |

This lab adds four machines to the catalogue while you play it. They stay
after `dsoxlab clean`; `dsoxlab destroy --optional-hosts` removes them.

```bash
dsoxlab run   cka-control-plane-haute-disponibilite
dsoxlab check cka-control-plane-haute-disponibilite
```
