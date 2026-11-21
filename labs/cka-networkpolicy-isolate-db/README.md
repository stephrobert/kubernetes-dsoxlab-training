# Isolate the database: only the backend gets in

The lesson shows a NetworkPolicy that lets only one client into a database.
This course measures each rule with a connection test, and adds cases the
lesson does not show: a port named instead of numbered, a list of clients with
`matchExpressions`, two policies that add up, a kubelet probe that gets
through a full deny, and a client that shares a node's network.

You work in a scratch namespace, `essai-np`, with a server `coffre` ("safe")
and four clients: `guichet`, `migration`, `sauvegarde` and `curieux`
("counter", "migration", "backup" and "nosy"). The challenge is about other
objects: you will do it on your own, at the end.

Related page: [Network Policies](https://www.stephane-robert.info/en/docs/devsecops/runtime/network-policies/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-networkpolicy-isolate-db
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The Pod network is
provided by Calico, which enforces NetworkPolicies.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create the namespace, then the server and the four clients. The server
listens on port 7000, declared under the name `coffre-http`, and it is placed
on the worker `k8s-w1.lab` (`nodeName`):

```bash
kubectl create namespace essai-np
cat <<YAML | kubectl apply -n essai-np -f -
apiVersion: v1
kind: Pod
metadata:
  name: coffre
  labels: {app: coffre}
spec:
  nodeName: k8s-w1.lab
  containers:
    - name: coffre
      image: registry.k8s.io/e2e-test-images/agnhost:2.53
      args: [netexec, --http-port=7000]
      ports:
        - {name: coffre-http, containerPort: 7000}
      readinessProbe:
        httpGet: {path: /healthz, port: coffre-http}
        periodSeconds: 3
YAML
kubectl expose pod coffre --port=7000 -n essai-np
for c in guichet migration sauvegarde curieux; do kubectl run $c --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-np --labels=app=$c -- sleep 3600 >/dev/null; done
kubectl wait --for=condition=Ready pod --all -n essai-np --timeout=120s
```

```text
namespace/essai-np created
pod/coffre created
service/coffre exposed
pod/coffre condition met
pod/curieux condition met
pod/guichet condition met
pod/migration condition met
pod/sauvegarde condition met
```

Each test in this course runs `nc -z` from each client to the `coffre`
Service, port 7000, with a 3-second timeout. `ouvert` ("open") means the
connection succeeded, `ferme` ("closed") means it failed. With no policy at
all, everyone gets in:

```bash
for c in guichet migration sauvegarde curieux; do printf '%-11s -> ' $c; kubectl exec $c -n essai-np -- nc -z -w 3 coffre 7000 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
guichet     -> ouvert
migration   -> ouvert
sauvegarde  -> ouvert
curieux     -> ouvert
```

## 🏷️ Exercise 1: a port named instead of numbered

Create a policy that lets only `guichet` in, on the port named `coffre-http`
rather than on its number:

```bash
cat <<'YAML' | kubectl apply -n essai-np -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: coffre-guichet
spec:
  podSelector:
    matchLabels: {app: coffre}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: {app: guichet}
      ports:
        - port: coffre-http
YAML
sleep 5
```

```text
networkpolicy.networking.k8s.io/coffre-guichet created
```

```bash
for c in guichet migration sauvegarde curieux; do printf '%-11s -> ' $c; kubectl exec $c -n essai-np -- nc -z -w 3 coffre 7000 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
guichet     -> ouvert
migration   -> ferme
sauvegarde  -> ferme
curieux     -> ferme
```

Only `guichet` gets in. The name `coffre-http` is looked up in the ports
declared by the target Pod's container. The benefit: if the application
changes port, you only change the Pod, the policy follows.

## 📋 Exercise 2: a list of clients with matchExpressions

`matchLabels` requires an exact value. To allow two clients in the same rule,
replace it with `matchExpressions` and the `In` operator:

```bash
kubectl patch networkpolicy coffre-guichet -n essai-np --type json -p '[{"op":"replace","path":"/spec/ingress/0/from/0/podSelector","value":{"matchExpressions":[{"key":"app","operator":"In","values":["guichet","migration"]}]}}]'; sleep 5
```

```text
networkpolicy.networking.k8s.io/coffre-guichet patched
```

```bash
for c in guichet migration sauvegarde curieux; do printf '%-11s -> ' $c; kubectl exec $c -n essai-np -- nc -z -w 3 coffre 7000 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
guichet     -> ouvert
migration   -> ouvert
sauvegarde  -> ferme
curieux     -> ferme
```

`guichet` and `migration` get in, the other two stay out.

## ➕ Exercise 3: two policies add up

Create a second, separate policy that opens the server to `sauvegarde`:

```bash
cat <<'YAML' | kubectl apply -n essai-np -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: coffre-sauvegarde
spec:
  podSelector:
    matchLabels: {app: coffre}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: {app: sauvegarde}
      ports:
        - port: 7000
YAML
sleep 5
```

```text
networkpolicy.networking.k8s.io/coffre-sauvegarde created
```

```bash
for c in guichet migration sauvegarde curieux; do printf '%-11s -> ' $c; kubectl exec $c -n essai-np -- nc -z -w 3 coffre 7000 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
guichet     -> ouvert
migration   -> ouvert
sauvegarde  -> ouvert
curieux     -> ferme
```

Three clients get in. Policies that target the same Pod add up: each one adds
permissions, none removes any. There is no "deny" rule in a NetworkPolicy. To
know who can reach a Pod, you must therefore read every policy that targets
it, not only the last one.

## 🚫 Exercise 4: the kubelet probe under a full deny

A policy that targets the server with no `ingress` rule at all denies every
incoming connection. Create it, and delete the other two:

```bash
cat <<'YAML' | kubectl apply -n essai-np -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tout-fermer
spec:
  podSelector:
    matchLabels: {app: coffre}
  policyTypes: [Ingress]
YAML
kubectl delete networkpolicy coffre-guichet coffre-sauvegarde -n essai-np; sleep 10
```

```text
networkpolicy.networking.k8s.io/tout-fermer created
networkpolicy.networking.k8s.io "coffre-guichet" deleted from essai-np namespace
networkpolicy.networking.k8s.io "coffre-sauvegarde" deleted from essai-np namespace
```

```bash
for c in guichet migration sauvegarde curieux; do printf '%-11s -> ' $c; kubectl exec $c -n essai-np -- nc -z -w 3 coffre 7000 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
guichet     -> ferme
migration   -> ferme
sauvegarde  -> ferme
curieux     -> ferme
```

Nobody gets in any more. Yet the server has a `readinessProbe`: every 3
seconds, the kubelet calls `/healthz` on its port. Look at its state
(`redémarrages` means "restarts"):

```bash
kubectl get pod coffre -n essai-np -o jsonpath='{.status.conditions[?(@.type=="Ready")].status} redémarrages={.status.containerStatuses[0].restartCount}{"\n"}'
```

```text
True redémarrages=0
```

The Pod is still Ready, with no restart. With Calico, the node that hosts a
Pod can always reach it, whatever the policy: that is what lets the kubelet
probe through. A full deny therefore does not make a Pod NotReady. The next
exercise shows the other side of this rule.

## 🏠 Exercise 5: a client that shares a node's network

Create two `hostNetwork` clients, with the `app=guichet` label: one on the
worker, next to the server, and one on the control plane:

```bash
for n in w1 cp; do kubectl run hote-$n --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-np --labels=app=guichet --overrides="{\"spec\":{\"hostNetwork\":true,\"nodeName\":\"k8s-$n.lab\"}}" -- sleep 3600; done; kubectl wait --for=condition=Ready pod/hote-w1 pod/hote-cp -n essai-np --timeout=120s; kubectl get pods -n essai-np -o wide | awk '{print $1, $6, $7}'
```

```text
pod/hote-w1 created
pod/hote-cp created
pod/hote-w1 condition met
pod/hote-cp condition met
NAME IP NODE
coffre 10.244.38.110 k8s-w1.lab
curieux 10.244.38.105 k8s-w1.lab
guichet 10.244.38.119 k8s-w1.lab
hote-cp 10.10.50.11 k8s-cp.lab
hote-w1 10.10.50.12 k8s-w1.lab
migration 10.244.38.66 k8s-w1.lab
sauvegarde 10.244.38.118 k8s-w1.lab
```

The two new clients carry their node's address. First try to reach the server
by name from `hote-cp`:

```bash
kubectl exec hote-cp -n essai-np -- nc -z -w 3 coffre 7000; echo "code $?"; kubectl exec hote-cp -n essai-np -- cat /etc/resolv.conf
```

```text
nc: bad address 'coffre'
command terminated with exit code 1
code 1
search lab
nameserver 10.10.50.1
```

`bad address 'coffre'`: the name does not resolve. A `hostNetwork` Pod
receives the node's `/etc/resolv.conf`, which does not know the cluster's
names. Without knowing this, you would think the policy refused it. The next
tests therefore use the Pod's address.

Replace the full deny with the policy that lets only `app=guichet` in:

```bash
kubectl delete networkpolicy tout-fermer -n essai-np; cat <<'YAML' | kubectl apply -n essai-np -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: coffre-guichet
spec:
  podSelector:
    matchLabels: {app: coffre}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: {app: guichet}
YAML
sleep 5
```

```text
networkpolicy.networking.k8s.io "tout-fermer" deleted from essai-np namespace
networkpolicy.networking.k8s.io/coffre-guichet created
```

```bash
IP=$(kubectl get pod coffre -n essai-np -o jsonpath='{.status.podIP}'); for c in guichet hote-w1 hote-cp; do printf '%-11s -> ' $c; kubectl exec $c -n essai-np -- nc -z -w 3 $IP 7000 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
guichet     -> ouvert
hote-w1     -> ouvert
hote-cp     -> ferme
```

All three clients carry the same label, and yet `hote-cp` is refused. For
Calico, a `hostNetwork` Pod is not a Pod: its traffic comes from the node's
address, and `podSelector` does not recognise it. `hote-w1` gets through for
the reason seen in exercise 4: it is on the node that hosts the server.

## 🧹 Clean-up

Delete the scratch namespace. The Pods, the Service and the policies go with
it:

```bash
kubectl delete namespace essai-np
```

```text
namespace "essai-np" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-networkpolicy-isolate-db
dsoxlab check cka-networkpolicy-isolate-db
```

```text
╭─ Result: cka-networkpolicy-isolate-db ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/8 tests       │
╰────────────────────────────────────────╯
```

0 out of 8: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a database that only the backend must be
able to reach.

```bash
dsoxlab run cka-networkpolicy-isolate-db
dsoxlab challenge cka-networkpolicy-isolate-db
```
