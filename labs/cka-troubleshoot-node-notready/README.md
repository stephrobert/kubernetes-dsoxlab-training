# Bring a NotReady node back into the cluster

The lesson shows how to troubleshoot a `NotReady` node. In this lab, the
worker is down: that is the challenge. This course stops the control plane's
kubelet for a minute, to watch what the cluster sees when a node goes silent,
and adds cases the lesson does not show: the lease the node renews, the
conditions that turn `Unknown`, the taints set by the controller, and the
return when the agent restarts.

The API server keeps answering during the stop: it is a static Pod already
running, and the stopped kubelet does not kill it.

Related page: [Troubleshoot a node](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/troubleshoot-a-node/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-troubleshoot-node-notready
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 💓 Exercise 1: a node's heartbeat

Each node renews a lease (a Lease object in the `kube-node-lease` namespace)
every few seconds. Read its renewal time twice, 12 seconds apart
(`renouvelé` means "renewed", `maintenant` "now"):

```bash
kubectl get lease k8s-cp.lab -n kube-node-lease -o jsonpath='renouvelé={.spec.renewTime}{"\n"}'; date -u +'maintenant=%Y-%m-%dT%H:%M:%S'; sleep 12; kubectl get lease k8s-cp.lab -n kube-node-lease -o jsonpath='renouvelé={.spec.renewTime}{"\n"}'; date -u +'maintenant=%Y-%m-%dT%H:%M:%S'
```

```text
renouvelé=2026-11-21T06:29:46.643024Z
maintenant=2026-11-21T06:29:53
renouvelé=2026-11-21T06:29:56.870270Z
maintenant=2026-11-21T06:30:05
```

The lease was renewed between the two reads. Also read the node's
conditions:

```bash
kubectl get node k8s-cp.lab -o jsonpath='{range .status.conditions[*]}{.type}={.status} ({.lastHeartbeatTime}){"\n"}{end}'
```

```text
NetworkUnavailable=False (2026-11-21T05:56:25Z)
MemoryPressure=False (2026-11-21T06:29:26Z)
DiskPressure=False (2026-11-21T06:29:26Z)
PIDPressure=False (2026-11-21T06:29:26Z)
Ready=True (2026-11-21T06:29:26Z)
```

All is well, and each condition carries the time of the kubelet's last
report.

## 🔇 Exercise 2: stop the control plane's agent

Stop this node's kubelet, and wait for the cluster to declare it `Unknown`.
The command times the wait (`NotReady au bout de` means "NotReady after"):

```bash
sudo systemctl stop kubelet; debut=$(date +%s); kubectl wait --for=condition=Ready=Unknown node/k8s-cp.lab --timeout=180s; echo "NotReady au bout de $(( $(date +%s) - debut )) s"; kubectl get lease k8s-cp.lab -n kube-node-lease -o jsonpath='renouvelé={.spec.renewTime}{"\n"}'; date -u +'maintenant=%Y-%m-%dT%H:%M:%S'; kubectl get nodes
```

```text
node/k8s-cp.lab condition met
NotReady au bout de 46 s
renouvelé=2026-11-21T06:29:56.870270Z
maintenant=2026-11-21T06:30:51
NAME         STATUS     ROLES           AGE    VERSION
k8s-cp.lab   NotReady   control-plane   157m   v1.37.2
k8s-w1.lab   NotReady   <none>          150m   v1.37.2
```

After some forty seconds without a renewed lease, the node controller marked
`k8s-cp.lab` `NotReady`. The worker is `NotReady` too, but for another reason:
that is the challenge. Read the conditions and the taints:

```bash
kubectl get node k8s-cp.lab -o jsonpath='{range .status.conditions[*]}{.type}={.status} {.reason}{"\n"}{end}{range .spec.taints[*]}taint {.key}:{.effect}{"\n"}{end}'
```

```text
NetworkUnavailable=False CalicoIsUp
MemoryPressure=Unknown NodeStatusUnknown
DiskPressure=Unknown NodeStatusUnknown
PIDPressure=Unknown NodeStatusUnknown
Ready=Unknown NodeStatusUnknown
taint node.kubernetes.io/unreachable:NoSchedule
taint node.kubernetes.io/unreachable:NoExecute
```

Every condition coming from the kubelet turns `Unknown`: nobody answers for
them any more. The controller sets two `unreachable` taints. `NoSchedule`
blocks new Pods. `NoExecute` evicts the node's Pods: each Pod automatically
gets a 300-second toleration for this taint, so it is evicted after 5 minutes
of absence.

## 🔊 Exercise 3: the agent restarts, the node comes back

Restart the kubelet, wait for the node to be `Ready`, and read the taints
right away:

```bash
sudo systemctl start kubelet; kubectl wait --for=condition=Ready node/k8s-cp.lab --timeout=120s; kubectl get node k8s-cp.lab -o jsonpath='{range .spec.taints[*]}taint {.key}:{.effect}{"\n"}{end}'
```

```text
node/k8s-cp.lab condition met
taint node.kubernetes.io/unreachable:NoExecute
```

The node is `Ready`, but the `NoExecute` taint is still there. Read again 10
seconds later:

```bash
sleep 10; kubectl get node k8s-cp.lab -o jsonpath='taints={.spec.taints}{"\n"}'
```

```text
taints=
```

No taint left: the controller removes them shortly after the node returns. A
node `NotReady` for a few minutes therefore leaves no trace, provided its Pods
tolerated the absence.

## 🧹 Clean-up

Check that the kubelet runs and the node is ready:

```bash
systemctl is-active kubelet; kubectl get node k8s-cp.lab
```

```text
active
NAME         STATUS   ROLES           AGE    VERSION
k8s-cp.lab   Ready    control-plane   157m   v1.37.2
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-node-notready
dsoxlab check cka-troubleshoot-node-notready
```

```text
╭─ Result: cka-troubleshoot-node-notready ─╮
│  0 / 100 pts                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests         │
╰──────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a `NotReady` worker to bring back into the
cluster, for good.

```bash
dsoxlab run cka-troubleshoot-node-notready
dsoxlab challenge cka-troubleshoot-node-notready
```
