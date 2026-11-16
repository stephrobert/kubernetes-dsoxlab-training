# Capture the traffic of a Pod and name the cause of each failure

Guided lab of the lesson "Capture the traffic of a Pod at packet level",
level 6 "Advanced networking" of the Kubernetes course (CKNE objective
"Using Linux Tools (iptables, ip, tcpdump) for Packet-level Issues"). Three
client Pods fail in three different ways: capture their traffic with
tcpdump, nsenter or kubectl debug, and name each cause from the packets.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster (Calico), grown with the optional second worker `k8s-w2.lab` |
| Duration | about 40 minutes |
| Prerequisite | the networking basics of the CKA track (Pod network, Services, CoreDNS) |
| Related page | [Kubernetes course](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/), until the lesson is published |

```bash
dsoxlab run k8s-capturer-le-trafic-d-un-pod
dsoxlab check k8s-capturer-le-trafic-d-un-pod
```

## What you will be able to do

- Find the host side interface of a Pod from the route to its address.
- Capture inside the network namespace of a Pod with nsenter, or from an
  ephemeral container with kubectl debug.
- Tell a refused connection, dropped packets and a DNS failure apart from a
  capture: a reset, a SYN sent again with no answer, NXDomain answers.
