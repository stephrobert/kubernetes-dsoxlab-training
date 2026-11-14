# Bring a broken application and its cluster back into service

Challenge of the **Diagnose** module of the Kubernetes course (level 4), in the
Put into practice section of the "Troubleshooting a node" lesson: four failures
at once on the catalogue's kubeadm cluster, two on the application side (a
Deployment in `CrashLoopBackOff`, a Pod in `ImagePullBackOff`) and two on the
cluster side (an API server that no longer starts, a worker whose kubelet is
down). The cause of each failure is recorded before its repair. Ten states,
threshold 70, two blocking.

| | |
|---|---|
| Targets | `k8s-cp.lab`, the catalogue's kubeadm cluster, and `k8s-w1.lab` reachable over `ssh` from the control plane; the lab sets up the `commerce` namespace |
| Duration | about 60 minutes |
| Related page | [Troubleshooting a node: kubelet and NotReady](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/troubleshoot-a-node/) |

```bash
dsoxlab run    k8s-challenge-depanner-une-application
dsoxlab check  k8s-challenge-depanner-une-application
dsoxlab submit k8s-challenge-depanner-une-application
```

The setup leaves `kubectl` without an answer on purpose: the API server is the
last failure it sets up. `dsoxlab clean` gives the cluster back in working
order, API server and worker included.
