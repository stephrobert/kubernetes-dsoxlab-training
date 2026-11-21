# Repair a node's Pod network and read what the network says

The lesson shows the Pod network on a kind cluster: the address ranges, a Pod
reaching another one, a node whose network goes down. This course has you
read the same network on the lab's kubeadm cluster, which runs Calico, and
adds cases the lesson does not show: the route that leads to a Pod, a Pod that
shares the node's network, a refusal caused by a wrong port, a timeout caused
by a network rule, and an address that changes when the Pod is recreated.

You work in a scratch namespace, `essai-reseau`, with a server `web` (nginx)
and a Pod `client` (busybox). The challenge is about other objects: you will
do it on your own, at the end.

Related page: [Pod Networking](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/pod-networking/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-troubleshoot-networking
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The lab broke the Pod network of the worker `k8s-w1.lab`: that is the
challenge. This course does not touch it. All its Pods are placed on the
control plane, with `nodeName` in `--overrides`.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and Calico.

## 🛣️ Exercise 1: which route leads to a Pod?

Create the namespace, then a server and a client on the control plane:

```bash
kubectl create namespace essai-reseau
kubectl run web --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-reseau --overrides='{"spec":{"nodeName":"k8s-cp.lab"}}'; kubectl run client --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-reseau --overrides='{"spec":{"nodeName":"k8s-cp.lab"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/web pod/client -n essai-reseau --timeout=120s
```

```text
namespace/essai-reseau created
pod/web created
pod/client created
pod/web condition met
pod/client condition met
```

Note each Pod's address:

```bash
kubectl get pods -n essai-reseau -o custom-columns=NOM:.metadata.name,IP:.status.podIP,NOEUD:.spec.nodeName
```

```text
NOM      IP              NOEUD
client   10.244.163.39   k8s-cp.lab
web      10.244.163.40   k8s-cp.lab
```

Both addresses are in `10.244.0.0/16`, the cluster's Pod range. Now ask the
node's kernel where it would send a packet for `web`:

```bash
IP=$(kubectl get pod web -n essai-reseau -o jsonpath='{.status.podIP}'); ip route get $IP
```

```text
10.244.163.40 dev calid79caa05e8e src 10.10.50.11 uid 1001 
    cache 
```

The packet leaves through a `cali…` interface. Calico creates one such
interface for each Pod on the node: it is the node's end of the virtual cable
that goes into the Pod. List all the routes to the Pod range:

```bash
ip route | grep 10.244 | head -5
```

```text
10.244.38.64/26 via 10.10.50.12 dev enp1s0 proto 80 onlink 
blackhole 10.244.163.0/26 proto 80 
10.244.163.2 dev cali101be86f1b7 scope link metric 1024 
10.244.163.4 dev califb592c426d0 scope link metric 1024 
10.244.163.5 dev cali3a96b53951b scope link metric 1024 
```

Each Pod on the node has a route to its single address, through its
`cali…` interface. Calico
gives each node a block of 64 addresses (`/26`): the local block ends in
`blackhole`, so that an address without a Pod goes nowhere, and the worker's
block goes through that node's address, `10.10.50.12`. When a Pod does not
answer, this is the first question to ask: does a route to its address exist,
and where does it lead?

Check that `client` reaches `web` by its address:

```bash
IP=$(kubectl get pod web -n essai-reseau -o jsonpath='{.status.podIP}'); kubectl exec client -n essai-reseau -- wget -qO- -T 3 "http://$IP" | grep -o '<title>.*</title>'
```

```text
<title>Welcome to nginx!</title>
```

## 🏠 Exercise 2: a Pod that shares the node's network

With `hostNetwork: true`, a Pod has no address of its own: it uses the
node's. Create one:

```bash
kubectl run hote --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-reseau --overrides='{"spec":{"hostNetwork":true,"nodeName":"k8s-cp.lab"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/hote -n essai-reseau --timeout=120s
```

```text
pod/hote created
pod/hote condition met
```

Compare its address with the node's:

```bash
kubectl get pods -n essai-reseau -o custom-columns=NOM:.metadata.name,IP:.status.podIP,NOEUD:.spec.nodeName; kubectl get node k8s-cp.lab -o jsonpath='{.status.addresses[0].address}{"\n"}'
```

```text
NOM      IP              NOEUD
client   10.244.163.39   k8s-cp.lab
hote     10.10.50.11     k8s-cp.lab
web      10.244.163.40   k8s-cp.lab
10.10.50.11
```

`hote` carries the node's address, `10.10.50.11`, outside the Pod range. Look
at the interfaces it sees:

```bash
kubectl exec hote -n essai-reseau -- ip -4 addr show | grep inet
```

```text
    inet 127.0.0.1/8 scope host lo
    inet 10.10.50.11/24 brd 10.10.50.255 scope global dynamic enp1s0
    inet 10.244.163.0/32 scope global vxlan.calico
```

It sees the node's real interface (`enp1s0`) and Calico's tunnel. The CNI does
not handle this Pod: that is why the `calico-node` and `kube-proxy` Pods run
this way, and why they start even when a node's Pod network is down. When you
see a node address in a Pod's IP column, that Pod uses `hostNetwork`.

## 🚫 Exercise 3: a refusal that comes from the Pod

Expose `web` through a Service whose `targetPort` is wrong: nginx listens on
80, the Service sends to 8080.

```bash
kubectl expose pod web --name=porte --port=80 --target-port=8080 -n essai-reseau; kubectl get endpointslices -n essai-reseau -l kubernetes.io/service-name=porte
```

```text
service/porte exposed
NAME          ADDRESSTYPE   PORTS   ENDPOINTS       AGE
porte-z9fm4   IPv4          8080    10.244.163.40   0s
```

The Service does have an endpoint: `web`'s address, on port 8080. Nothing
shows the mistake yet. Call it and time the call:

```bash
kubectl exec client -n essai-reseau -- sh -c 'debut=$(date +%s); wget -qO- -T 5 "http://porte"; echo "code $? en $(( $(date +%s) - debut )) s"'
```

```text
wget: can't connect to remote host (10.103.132.190): Connection refused
code 1 en 1 s
```

`Connection refused`, almost at once (`code 1 en 1 s` reads "code 1 in 1 s").
The packet reached the Pod, and the Pod's kernel answered that nobody listens
on that port. An immediate refusal therefore says: the network works, the
port is wrong, or the application does not listen.

## ⏳ Exercise 4: a timeout that comes from a network rule

Create a second Service, correct this time, and put a label on `web`:

```bash
kubectl expose pod web --name=muet --port=80 -n essai-reseau; kubectl label pod web -n essai-reseau role=web
```

```text
service/muet exposed
pod/web labeled
```

Add a NetworkPolicy that closes all incoming traffic to the `role=web` Pods.
NetworkPolicies have their own lesson later in the course. Here, all you need
to know is that Calico then drops the packets silently, without answering:

```bash
cat <<'YAML' | kubectl apply -n essai-reseau -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: fermer-web
spec:
  podSelector:
    matchLabels:
      role: web
  policyTypes: [Ingress]
YAML
```

```text
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: fermer-web
spec:
  podSelector:
    matchLabels:
      role: web
  policyTypes: [Ingress]
YAML
networkpolicy.networking.k8s.io/fermer-web created
```

Call `muet`:

```bash
kubectl exec client -n essai-reseau -- sh -c 'debut=$(date +%s); wget -qO- -T 5 "http://muet"; echo "code $? en $(( $(date +%s) - debut )) s"'
```

```text
wget: download timed out
code 1 en 5 s
```

This time, `wget` waits for the 5 seconds of its timeout, then gives up.
Nobody answered. Call `porte` again, which refused at once in exercise 3:

```bash
kubectl exec client -n essai-reseau -- sh -c 'debut=$(date +%s); wget -qO- -T 5 "http://porte"; echo "code $? en $(( $(date +%s) - debut )) s"'
```

```text
wget: download timed out
code 1 en 5 s
```

The refusal became a timeout: the packet is dropped before it reaches the
Pod, so the Pod can no longer say the port is closed. Remember the rule: a
timeout means something on the path drops the packets (a network rule, a
missing route, a node whose network went down). A refusal means the path
works.

Remove the rule and check that `muet` answers again:

```bash
kubectl delete networkpolicy fermer-web -n essai-reseau; kubectl exec client -n essai-reseau -- sh -c 'wget -qO- -T 5 http://muet | grep -o "<title>.*</title>"'
```

```text
networkpolicy.networking.k8s.io "fermer-web" deleted from essai-reseau namespace
<title>Welcome to nginx!</title>
```

## 🔁 Exercise 5: the address changes, the name stays

Delete `web` and recreate it identically, with the `run=web` label that the
`muet` Service selects:

```bash
kubectl get pod web -n essai-reseau -o jsonpath='{.status.podIP}{"\n"}'; kubectl delete pod web -n essai-reseau; kubectl run web --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-reseau --labels=run=web --overrides='{"spec":{"nodeName":"k8s-cp.lab"}}'; kubectl wait --for=condition=Ready pod/web -n essai-reseau --timeout=120s; kubectl get pod web -n essai-reseau -o jsonpath='{.status.podIP}{"\n"}'
```

```text
10.244.163.40
pod "web" deleted from essai-reseau namespace
pod/web created
pod/web condition met
10.244.163.43
```

Same name, another address. Look at the Service:

```bash
kubectl get endpointslices -n essai-reseau -l kubernetes.io/service-name=muet; kubectl exec client -n essai-reseau -- sh -c 'wget -qO- -T 5 http://muet | grep -o "<title>.*</title>"'
```

```text
NAME         ADDRESSTYPE   PORTS   ENDPOINTS       AGE
muet-pg2cp   IPv4          80      10.244.163.43   12s
<title>Welcome to nginx!</title>
```

The EndpointSlice already carries the new address, and calling the name
`muet` works without changing anything. A Pod address written down by hand
only holds while the Pod lives: to reach an application, go through its
Service.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-reseau
```

```text
namespace "essai-reseau" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-networking
dsoxlab check cka-troubleshoot-networking
```

```text
╭─ Result: cka-troubleshoot-networking ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests      │
╰───────────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a worker whose Pod network went down, to be
repaired, then a refusal and a timeout to recognise. The reset already
prepared the challenge: do not run `dsoxlab run` again, as it waits for all
nodes to be Ready and fails while the worker is down. Display the
instructions, then connect to the machine again:

```bash
dsoxlab challenge cka-troubleshoot-networking
dsoxlab ssh k8s-cp.lab
```
