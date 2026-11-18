# Level 4 test: administer a cluster

The end-of-level-4 test of the Kubernetes course: administer, from an
inherited state, the kubeadm cluster that hosts the shop. Bring back a reset
worker, prove the high availability of a control plane behind its load
balancer, back up etcd and restore the shop from the previous day's backup,
migrate manifests off removed APIs, upgrade the cluster from 1.36.4 to 1.37.0,
keep the shop available during maintenance, repair a node, an API server and
a component after first recording each cause, carry a live change into the
repository and renew certificates. Eighteen criteria, threshold 70, seven
critical, no hint.

High availability runs on a kind cluster with three control planes, on
`k8s-kind.lab`, because the catalogue's infrastructure carries a single kubeadm
control plane. The setup rebuilds the kubeadm cluster in 1.36.4, and the
cleanup rebuilds it at the catalogue's version; it also deletes the other
labs' kind clusters, which each one recreates through its own setup.

| | |
|---|---|
| Target | `k8s-cp.lab` and `k8s-w1.lab`, the catalogue's kubeadm cluster; `k8s-kind.lab`, where the learner creates cluster `ha` |
| Duration | about 180 minutes |
| Related page | [Level 4 exam: administer a cluster](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/exam-administer-a-cluster/) |

```bash
dsoxlab run    k8s-epreuve-administrer-un-cluster
dsoxlab check  k8s-epreuve-administrer-un-cluster
dsoxlab submit k8s-epreuve-administrer-un-cluster
```
