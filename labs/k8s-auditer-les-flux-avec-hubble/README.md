# Audit network flows with Hubble

Guided lab of the lesson "Observe, measure and audit flows with Hubble",
Advanced networking module of the Kubernetes course (level 6, CKNE objectives
of the Observability domain). A NetworkPolicy refuses one of three clients of
an API: find the flow with Hubble and record it, give the drop metric the
context that makes it name the Pod, and log only the refused flows to a file
on the node, without lifting the refusal.

| | |
|---|---|
| Target | `net-cp.lab`, with the workers `net-w1.lab` and `net-w2.lab`: the Cilium cluster of the catalogue; the lab sets up the `magasin` namespace |
| Duration | about 40 minutes |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (which declares Kubernetes 1.33 to 1.36), Helm 4.3.2 |
| Related page | [Hubble](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/hubble/) |

The three nodes are optional hosts of the catalogue: `dsoxlab run` brings
them up the first time (8 GB of RAM in total), and builds the Cilium cluster
without kube-proxy if it is not there.

The method is in `scenario.md`: `hubble observe --verdict DROPPED` in the
agent of the destination node, the `hubble_drop_total` metric on port 9965,
then a `helm upgrade` that gives the drop metric a Pod context and turns on
the static export of the refused flows.

The `cleanup.yaml` brings Cilium back to the values of the catalogue
foundation (the agents restart), removes the export files from the three
nodes, then the `magasin` namespace. The cluster stays.

```bash
dsoxlab run   k8s-auditer-les-flux-avec-hubble
dsoxlab check k8s-auditer-les-flux-avec-hubble
```
