# Bring the API server back into service

The lesson shows how to troubleshoot a control plane when the API server no
longer answers. In this lab, it is down: that is the challenge, and kubectl is
useless. This course does not touch the API server. It has you check the
other components by their own means, and adds cases the lesson does not show:
each component's local health endpoint, a static component stopped then
restarted by moving its manifest, and etcd queried without the API.

The challenge is about the API server itself: you will do it on your own, at
the end.

Related page: [Troubleshoot a cluster](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-troubleshoot-apiserver
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). The node's tools (`crictl`, the files under
`/etc/kubernetes`) need `sudo`.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 🩺 Exercise 1: each component has its own health endpoint

The scheduler, the controller-manager and the kubelet each have a health
endpoint, on a local port of the node. Query them directly:

```bash
for p in 10259 10257; do printf 'port %s : ' $p; curl -sk "https://127.0.0.1:$p/healthz"; echo; done; printf 'kubelet 10248 : '; curl -s "http://127.0.0.1:10248/healthz"; echo
```

```text
port 10259 : ok
port 10257 : ok
kubelet 10248 : ok
```

All three answer `ok`, without going through the API server (the scheduler on
10259, the controller-manager on 10257, the kubelet on 10248). Compare with
kubectl:

```bash
kubectl get nodes --request-timeout=5s 2>&1 | tail -1
```

```text
The connection to the server 10.10.50.11:6443 was refused - did you specify the right host or port?
```

Connection refused on port 6443: the API server is what is missing, not the
whole control plane. Querying each component separates what works from what
does not.

## 🔁 Exercise 2: stop and restart a static component without the API

The control plane's components are static Pods: the kubelet starts them from
the files in `/etc/kubernetes/manifests`. Count the scheduler's containers:

```bash
sudo crictl ps --name kube-scheduler -o json | python3 -c 'import json,sys; c=json.load(sys.stdin)["containers"]; print(len(c), "conteneur(s) kube-scheduler")'
```

```text
1 conteneur(s) kube-scheduler
```

Move its manifest out of the directory, wait, then count again and query its
port:

```bash
sudo mv /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/kube-scheduler.yaml; sleep 25; sudo crictl ps --name kube-scheduler -q | wc -l; printf 'port 10259 : '; curl -sk -m 3 "https://127.0.0.1:10259/healthz"; echo " (code $?)"
```

```text
0
port 10259 :  (code 7)
```

No container left, and the port no longer answers (curl code 7: cannot
connect). The kubelet stopped the Pod as soon as its file disappeared. Put
the manifest back:

```bash
sudo mv /tmp/kube-scheduler.yaml /etc/kubernetes/manifests/kube-scheduler.yaml; sleep 30; sudo crictl ps --name kube-scheduler | tail -1 | cut -c1-110; printf 'port 10259 : '; curl -sk "https://127.0.0.1:10259/healthz"; echo
```

```text
7a2cf2aca8597       20824b0c11f7d       29 seconds ago      Running             kube-scheduler      1         
port 10259 : ok
```

The scheduler starts again, with a new container. Moving a manifest out of
the directory, rather than editing it in place, is the safe way to stop a
static component: the file is kept, and putting it back is enough.

## 🗄️ Exercise 3: etcd answers, even when the API is silent

etcd is a static Pod too. Get into its container with `crictl exec`, without
the API, and ask for its health:

```bash
C=$(sudo crictl ps --name etcd -q | head -1); sudo crictl exec $C etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key endpoint health
```

```text
127.0.0.1:2379 is healthy: successfully committed proposal: took = 5.624025ms
```

Healthy. Read the first namespaces stored in the database:

```bash
C=$(sudo crictl ps --name etcd -q | head -1); sudo crictl exec $C etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /registry/namespaces --prefix --keys-only | head -5
```

```text
/registry/namespaces/calico-system

/registry/namespaces/default

/registry/namespaces/kube-node-lease
```

The cluster's data is intact: only the server that exposes it is down.
Knowing etcd is fine saves you from looking for the failure in the wrong
place.

## 🧹 Clean-up

Check that the scheduler's manifest is back in its place (the line reads
"scheduler manifest in place"):

```bash
sudo test -f /etc/kubernetes/manifests/kube-scheduler.yaml && echo 'manifeste du scheduler en place'
```

```text
manifeste du scheduler en place
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-apiserver
dsoxlab check cka-troubleshoot-apiserver
```

```text
╭─ Result: cka-troubleshoot-apiserver ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests     │
╰──────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: an API server that no longer starts, to
bring back into service without opening it to everyone.

```bash
dsoxlab run cka-troubleshoot-apiserver
dsoxlab challenge cka-troubleshoot-apiserver
```
