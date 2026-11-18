# Connect two clusters with Cilium ClusterMesh

Guided lab of the lesson "Connect two clusters with ClusterMesh", level 6
"Advanced networking" of the Kubernetes course (CKNE). Connect two
single-node Cilium clusters that share a certificate authority, make a Service
global, and prove that a Pod of the first cluster reaches the backends of
both.

| | |
|---|---|
| Target | `ha-cp1.lab` (cluster-1) and `ha-cp2.lab` (cluster-2), two optional hosts, one single-node cluster each |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (which declares Kubernetes 1.33 to 1.36), CLI cilium v0.20.3, Helm 4.3.2 |
| Duration | about 30 minutes, plus the setup that builds the two clusters |
| Prerequisite | the lab `k8s-installer-cilium-sans-kube-proxy` |
| Related page | [ClusterMesh](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/clustermesh/) |

The `run` of this lab mounts `ha-cp1.lab` and `ha-cp2.lab` if they are not
running yet, resets them, builds the two clusters and installs Cilium on both
with the same certificate authority. The `cleanup.yaml` resets both nodes to
"ready, no cluster", the state that the lab
`cka-control-plane-haute-disponibilite` also expects on these hosts.

```bash
dsoxlab run   k8s-relier-deux-clusters
dsoxlab check k8s-relier-deux-clusters
```
