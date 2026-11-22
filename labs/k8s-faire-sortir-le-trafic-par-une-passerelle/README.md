# Send traffic out through a gateway

The lesson enables Cilium's egress gateway so that a Pod always leaves the
cluster through the same node, hence with the same address. That is also the
challenge of this lab: this course enables nothing and writes no policy. It
looks at how traffic leaves **today**, without a gateway: which address an
outside server sees depending on the Pod's node, which rule rewrites that
address, and when it does not rewrite it. That is what you need to know to
understand what the gateway changes.

You work in the `essai-sortie` namespace, with two scratch clients and two
scratch servers. The challenge uses other Pods, in `egress-demo`: you will do
it on your own, at the end.

Related page: [Send traffic out through an egress gateway](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/egress-gateway/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-faire-sortir-le-trafic-par-une-passerelle
```

You are now connected to `net-cp.lab`, the control plane of the Cilium
cluster. The lab's witness server runs on `k8s-cp.lab`, outside the cluster,
and answers with the source address it sees. Create the scratch objects: a
client on each worker, a web server on `net-w2`, and a second web server on
`net-w2` that shares the node's network (`hostNetwork: true`):

```bash
kubectl create namespace essai-sortie; cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: client-w1
  namespace: essai-sortie
spec:
  nodeName: net-w1.lab
  containers:
    - name: c
      image: busybox:1.38.0
      command: ["sleep", "3600"]
---
apiVersion: v1
kind: Pod
metadata:
  name: client-w2
  namespace: essai-sortie
spec:
  nodeName: net-w2.lab
  containers:
    - name: c
      image: busybox:1.38.0
      command: ["sleep", "3600"]
---
apiVersion: v1
kind: Pod
metadata:
  name: web-w2
  namespace: essai-sortie
spec:
  nodeName: net-w2.lab
  containers:
    - name: web
      image: nginx:1.30.6
---
apiVersion: v1
kind: Pod
metadata:
  name: web-hote-w2
  namespace: essai-sortie
spec:
  nodeName: net-w2.lab
  hostNetwork: true
  containers:
    - name: web
      image: nginx:1.30.6
YAML
kubectl -n essai-sortie wait --for=condition=Ready pod --all --timeout=120s
kubectl -n essai-sortie get pods -o wide
```

```text
NAME          READY   STATUS    RESTARTS   AGE   IP             NODE         NOMINATED NODE   READINESS GATES
client-w1     1/1     Running   0          1s    10.244.1.245   net-w1.lab   <none>           <none>
client-w2     1/1     Running   0          1s    10.244.2.10    net-w2.lab   <none>           <none>
web-hote-w2   1/1     Running   0          1s    10.10.50.16    net-w2.lab   <none>           <none>
web-w2        1/1     Running   0          1s    10.244.2.197   net-w2.lab   <none>           <none>
```

`web-hote-w2` carries the address of the `net-w2` node, `10.10.50.16`: it
listens directly on the node. The outputs shown in this course were captured
on these machines on 22 November 2026 (Kubernetes v1.37.2, Cilium 1.20.5).

## 🌐 Exercise 1: the exit address depends on the node

Read the witness address in the lab's ConfigMap, then call it from each
client:

```bash
temoin=$(kubectl -n egress-demo get cm -o jsonpath='{.items[*].data.url}')
echo "$temoin"
for p in client-w1 client-w2; do echo "$p -> $(kubectl -n essai-sortie exec $p -- wget -qO- $temoin)"; done
```

```text
http://10.10.50.11:8090/
client-w1 -> 10.10.50.15
client-w2 -> 10.10.50.16
```

The witness never sees a Pod address (`10.244.x.x`): it sees the address of
the **node** that runs the Pod, `10.10.50.15` for `net-w1` and `10.10.50.16`
for `net-w2`. The same Pod, moved to another node, would leave with another
address. An outside firewall that allows a single address therefore cannot
target a Pod. This is the problem the egress gateway solves.

## 🔁 Exercise 2: the rule that rewrites the address

This cluster masquerades addresses with iptables: the
`Masquerading: IPTables` line the lesson shows. Cilium puts its rule in the
`CILIUM_POST_nat` chain of each node. Read the one on `net-w1`, and its
counter before and after a call to the witness:

```bash
ssh net-w1.lab 'sudo iptables -t nat -S CILIUM_POST_nat | grep non-cluster'
ssh net-w1.lab 'sudo iptables -t nat -L CILIUM_POST_nat -n -v -x | grep non-cluster' | awk '{print "avant :", $1, "paquets"}'
kubectl -n essai-sortie exec client-w1 -- wget -qO- $temoin
ssh net-w1.lab 'sudo iptables -t nat -L CILIUM_POST_nat -n -v -x | grep non-cluster' | awk '{print "après :", $1, "paquets"}'
```

```text
-A CILIUM_POST_nat -s 10.244.1.0/24 ! -d 10.244.1.0/24 ! -o cilium_+ -m comment --comment "cilium masquerade non-cluster" -j MASQUERADE
avant : 6 paquets
10.10.50.15
après : 7 paquets
```

The rule reads as three conditions (`avant` means before, `après` after). The
packet comes from a Pod of this node (`-s 10.244.1.0/24`, the address block of
`net-w1`), it is not going to a Pod of this node (`! -d 10.244.1.0/24`), and it
does not leave through a Cilium interface (`! -o cilium_+`). Then
`MASQUERADE` replaces its source with the address of the outgoing interface.
The counter only moves by **one** packet for the whole HTTP request: only the
first packet of a connection goes through the `nat` table, the kernel then
applies the same translation to the rest of the connection.

## 🔀 Exercise 3: from Pod to Pod, the address is kept

Now call the `web-w2` server, on the other node, by its Pod address, and read
in its log the address it saw:

```bash
web=$(kubectl -n essai-sortie get pod web-w2 -o jsonpath='{.status.podIP}')
cip=$(kubectl -n essai-sortie get pod client-w1 -o jsonpath='{.status.podIP}')
echo "client-w1=$cip web-w2=$web"
kubectl -n essai-sortie exec client-w1 -- wget -qO /dev/null "http://$web/?essai-pod"
kubectl -n essai-sortie logs web-w2 | grep essai-pod | cut -d' ' -f1-7
```

```text
client-w1=10.244.1.245 web-w2=10.244.2.197
10.244.1.245 - - [22/Nov/2026:22:39:52 +0000] "GET /?essai-pod
```

The server sees `10.244.1.245`, the address of the client Pod: nothing was
masqueraded. The packet was going outside the `net-w1` block, but it left
through Cilium's tunnel, a `cilium_*` interface, and the third condition of
the rule let it through. Between two Pods, Kubernetes requires that each one
sees the real address of the other, and this is what lets a NetworkPolicy
recognise the source.

## 🖥️ Exercise 4: towards a node, the address is masqueraded

Finally call `web-hote-w2`, which listens on the `net-w2` node itself, by the
node's address:

```bash
kubectl -n essai-sortie exec client-w1 -- wget -qO /dev/null "http://10.10.50.16/?essai-noeud"
kubectl -n essai-sortie logs web-hote-w2 | grep essai-noeud | cut -d' ' -f1-7
```

```text
10.10.50.15 - - [22/Nov/2026:22:39:52 +0000] "GET /?essai-noeud
```

Same client, same destination node, but this time the server sees
`10.10.50.15`, the address of `net-w1`. The destination, `10.10.50.16`, is not
a Pod address: the packet left through `enp1s0`, the interface of the node
network, and the rule of exercise 2 masqueraded it. What decides is not the
machine you target, but **the interface the packet leaves through**.

## 🧹 Clean-up

Delete the scratch namespace, and check that the two Pods of the challenge are
still there:

```bash
kubectl delete namespace essai-sortie --wait=true --timeout=120s
kubectl -n egress-demo get pods
```

```text
namespace "essai-sortie" deleted
NAME               READY   STATUS    RESTARTS   AGE
autre              1/1     Running   0          2m12s
sortie-controlee   1/1     Running   0          2m12s
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the
clean-up and then the lab preparation: you get back exactly the starting state
of the challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-faire-sortir-le-trafic-par-une-passerelle
dsoxlab check k8s-faire-sortir-le-trafic-par-une-passerelle
```

```text
╭─ Result: k8s-faire-sortir-le-trafic-par-une-passerelle ─╮
│  0 / 100 pts                                            │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                        │
╰─────────────────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for
you, untouched.

## 🎯 The challenge

Your turn, on your own this time: enable the egress gateway and send a single
Pod out through a chosen node, while its neighbour keeps leaving through its
own.

```bash
dsoxlab run k8s-faire-sortir-le-trafic-par-une-passerelle
dsoxlab challenge k8s-faire-sortir-le-trafic-par-une-passerelle
```
