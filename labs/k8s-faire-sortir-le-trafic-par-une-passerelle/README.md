# Send a Pod's traffic out through an egress gateway

Guided lab of the lesson "Send traffic out through an egress gateway", level 6
"Advanced networking" of the Kubernetes course (CKNE). Turn on the Cilium
egress gateway with the BPF masquerading it requires, designate a gateway
node, and make one Pod, and only that one, reach an external server through
that node.

| | |
|---|---|
| Target | `net-cp.lab`, the Cilium cluster without kube-proxy of the optional hosts `net-cp`, `net-w1` and `net-w2`; the witness server runs on `k8s-cp.lab`, outside that cluster |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (which declares Kubernetes 1.33 to 1.36), Helm 4.3.2 |
| Duration | about 30 minutes |
| Prerequisite | the lab `k8s-installer-cilium-sans-kube-proxy` |
| Related page | [Egress gateway](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/egress-gateway/) |

The `run` of this lab mounts the `net-*` hosts if they are not running yet,
brings Cilium back to the values of the base cluster, and starts the witness
server on `k8s-cp.lab` (port 8090, a transient systemd unit). The
`cleanup.yaml` deletes the policies and the namespace `egress-demo`, removes
the gateway label from the nodes, brings Cilium back to the base values, and
stops the witness.

```bash
dsoxlab run   k8s-faire-sortir-le-trafic-par-une-passerelle
dsoxlab check k8s-faire-sortir-le-trafic-par-une-passerelle
```
