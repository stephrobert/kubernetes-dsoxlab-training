# Install Cilium without kube-proxy

Guided lab of the lesson "Install Cilium without kube-proxy and choose its
IPAM", Advanced networking module of the Kubernetes course (level 6, CKNE
objectives of the Core Infrastructure and CNI domain). Initialise a kubeadm
cluster without kube-proxy, join two workers, install Cilium 1.20.5 with Helm
as the kube-proxy replacement on the pool `10.244.0.0/16`, then prove that a
Service is served by Cilium and not by iptables rules.

| | |
|---|---|
| Target | `net-cp.lab`, with the workers `net-w1.lab` and `net-w2.lab`: the Cilium cluster of the catalogue, separate from the shared cluster `k8s-cp.lab` |
| Duration | about 45 minutes |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (which declares Kubernetes 1.33 to 1.36), Helm 4.3.2 |
| Related page | [Cilium](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cilium/) |

The three nodes are optional hosts of the catalogue: `dsoxlab run` brings
them up the first time (8 GB of RAM in total), and `dsoxlab destroy
--optional-hosts` removes them.

The method is in `scenario.md`: `kubeadm init --skip-phases=addon/kube-proxy`,
`kubeadm join` on both workers, `helm install` with `kubeProxyReplacement`,
`k8sServiceHost`, `k8sServicePort` and the cluster-pool IPAM, then the reading
of `cilium-dbg status`, of the nat tables and of a Service.

The `cleanup.yaml` resets the three nodes with `kubeadm reset`, removes the
CNI configuration, the state of the Cilium agent and the KUBE and CILIUM
chains: the next lab rebuilds the ready cluster.

```bash
dsoxlab run   k8s-installer-cilium-sans-kube-proxy
dsoxlab check k8s-installer-cilium-sans-kube-proxy
```
