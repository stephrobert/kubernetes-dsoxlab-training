# Repair, open, route out and audit the flows of a Cilium cluster, without guidance

Challenge of the **Advanced networking** module of the Kubernetes course
(level 6, CKNE), in the Practice section of the lesson "Route traffic out
through an egress gateway": a Service served by Cilium to repair without
kube-proxy, a single flow to open between two namespaces, a namespace to route
out through a chosen node, and the flow a policy refuses to name by reading it
in Hubble. Four states, pass mark 70.

| | |
|---|---|
| Target | `net-cp.lab`, Cilium 1.20.5 cluster without kube-proxy (`net-w1.lab`, `net-w2.lab`), egress gateway and Hubble enabled; external witness on `k8s-cp.lab` |
| Duration | about 60 minutes |
| Related page | [Route traffic out through an egress gateway](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/egress-gateway/) |

```bash
dsoxlab run    k8s-challenge-reseau-avance
dsoxlab check  k8s-challenge-reseau-avance
dsoxlab submit k8s-challenge-reseau-avance
```
