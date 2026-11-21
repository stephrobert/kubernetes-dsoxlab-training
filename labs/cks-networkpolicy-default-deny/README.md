# Deny everything, then reopen the strict minimum, DNS included

The lesson shows the zero-trust model: a policy that closes everything, then
policies that reopen the useful flows. This course measures each step and
adds cases the lesson does not show: a Pod created after the lockdown, a
"port 53 open everywhere" that lets through far more than DNS, reply
traffic, the API server behind a closed egress, and a removed label that cuts
an access.

You work in a scratch namespace, `essai-zc`, with a server `caisse`
("till", nginx) and a client `comptoir` ("counter", busybox), then in a
second namespace, `essai-dehors`. The challenge is about other objects: you
will do it on your own, at the end.

Related page: [Network Policies](https://www.stephane-robert.info/en/docs/devsecops/runtime/network-policies/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-networkpolicy-default-deny
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The Pod network is
provided by Calico, which enforces NetworkPolicies.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and busybox 1.38.

Create the namespace, the server exposed by a Service, and the client:

```bash
kubectl create namespace essai-zc; kubectl run caisse --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-zc --labels=app=caisse; kubectl expose pod caisse --port=80 -n essai-zc; kubectl run comptoir --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-zc --labels=app=comptoir -- sleep 3600; kubectl wait --for=condition=Ready pod --all -n essai-zc --timeout=120s
```

```text
namespace/essai-zc created
pod/caisse created
service/caisse exposed
pod/comptoir created
pod/caisse condition met
pod/comptoir condition met
```

## 🔒 Exercise 1: close everything, including for future Pods

With `podSelector: {}`, a policy targets every Pod in the namespace. With both
`Ingress` and `Egress` types and no rule, it closes incoming and outgoing
traffic:

```bash
cat <<'YAML' | kubectl apply -n essai-zc -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tout-fermer
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
YAML
sleep 5
```

```text
networkpolicy.networking.k8s.io/tout-fermer created
```

Create a Pod after the policy, then try to reach `caisse` from the old and
the new client (`ouvert` means "open", `ferme` means "closed"):

```bash
kubectl run tardif --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-zc -- sleep 3600; kubectl wait --for=condition=Ready pod/tardif -n essai-zc --timeout=120s; C=$(kubectl get pod caisse -n essai-zc -o jsonpath='{.status.podIP}'); for p in comptoir tardif; do printf '%-9s -> caisse : ' $p; kubectl exec $p -n essai-zc -- nc -z -w 3 $C 80 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
pod/tardif created
pod/tardif condition met
comptoir  -> caisse : ferme
tardif    -> caisse : ferme
```

`tardif` ("late") is closed too: the empty selector applies to present and
future Pods. Now try a name lookup:

```bash
kubectl exec tardif -n essai-zc -- nslookup -timeout=3 kubernetes.default; echo "code $?"
```

```text
;; connection timed out; no servers could be reached

command terminated with exit code 1
code 1
```

No DNS server can be reached any more: the closed egress also blocks DNS
questions. This is the first thing that breaks after a full lockdown.

## 🕳️ Exercise 2: a port 53 open to everywhere

A `relais` ("relay") server in another namespace listens over HTTP on port 53,
the DNS port:

```bash
kubectl create namespace essai-dehors; kubectl run relais --image=registry.k8s.io/e2e-test-images/agnhost:2.53 -n essai-dehors -- netexec --http-port=53; kubectl wait --for=condition=Ready pod/relais -n essai-dehors --timeout=120s
```

```text
namespace/essai-dehors created
pod/relais created
pod/relais condition met
```

Reopen egress on port 53, over UDP and TCP, without naming a destination. The
command then tests a lookup, then an HTTP call to `relais` on port 53. The
name is written in full with a final dot, so that busybox does not walk its
search list:

```bash
cat <<'YAML' | kubectl apply -n essai-zc -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-large
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - ports:
        - {protocol: UDP, port: 53}
        - {protocol: TCP, port: 53}
YAML
sleep 5; R=$(kubectl get pod relais -n essai-dehors -o jsonpath='{.status.podIP}'); kubectl exec comptoir -n essai-zc -- nslookup kubernetes.default.svc.cluster.local. | grep -A1 Name; kubectl exec comptoir -n essai-zc -- wget -qO- -T 3 "http://$R:53/hostname"; echo
```

```text
networkpolicy.networking.k8s.io/dns-large created
Name:	kubernetes.default.svc.cluster.local
Address: 10.96.0.1
relais
```

DNS works again, and `relais` answers too. The rule allows port 53 to any
address, whatever listens behind it. A program that wants to leave the
namespace only has to use that port. Replace it with a rule that targets only
the cluster's DNS Pods, in `kube-system`:

```bash
kubectl delete networkpolicy dns-large -n essai-zc; cat <<'YAML' | kubectl apply -n essai-zc -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-strict
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels: {kubernetes.io/metadata.name: kube-system}
          podSelector:
            matchLabels: {k8s-app: kube-dns}
      ports:
        - {protocol: UDP, port: 53}
        - {protocol: TCP, port: 53}
YAML
sleep 5; R=$(kubectl get pod relais -n essai-dehors -o jsonpath='{.status.podIP}'); kubectl exec comptoir -n essai-zc -- nslookup kubernetes.default.svc.cluster.local. | grep -A1 Name; kubectl exec comptoir -n essai-zc -- wget -qO- -T 3 "http://$R:53/hostname"; echo "wget : code $?"
```

```text
networkpolicy.networking.k8s.io "dns-large" deleted from essai-zc namespace
networkpolicy.networking.k8s.io/dns-strict created
Name:	kubernetes.default.svc.cluster.local
Address: 10.96.0.1
wget: download timed out
command terminated with exit code 1
wget : code 1
```

DNS still answers, but `relais` no longer gets through. An opening for DNS is
therefore written with its destination: the `kube-system` namespace and the
`k8s-app: kube-dns` label of the CoreDNS Pods.

## ↩️ Exercise 3: the reply goes through, the reverse initiative does not

Reopen the flow from `comptoir` to `caisse` on port 80. It takes two policies:
an egress for `comptoir` and an ingress for `caisse`, because the full
lockdown blocks both sides:

```bash
cat <<'YAML' | kubectl apply -n essai-zc -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: comptoir-vers-caisse
spec:
  podSelector:
    matchLabels: {app: comptoir}
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels: {app: caisse}
      ports:
        - {protocol: TCP, port: 80}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: caisse-depuis-comptoir
spec:
  podSelector:
    matchLabels: {app: caisse}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: {app: comptoir}
      ports:
        - {protocol: TCP, port: 80}
YAML
sleep 5; kubectl exec comptoir -n essai-zc -- wget -qO- -T 3 http://caisse | grep -o '<title>.*</title>'
```

```text
networkpolicy.networking.k8s.io/comptoir-vers-caisse created
networkpolicy.networking.k8s.io/caisse-depuis-comptoir created
<title>Welcome to nginx!</title>
```

The page arrives. You opened nothing for the reply from `caisse` to
`comptoir`: Calico tracks the connection, and the reply goes through with it.
Now start a connection the other way round, from `caisse` to `comptoir`:

```bash
P=$(kubectl get pod comptoir -n essai-zc -o jsonpath='{.status.podIP}'); kubectl exec caisse -n essai-zc -- sh -c "curl -s -m 3 -o /dev/null 'http://$P:8080/'; echo code \$?"
```

```text
code 28
```

Code 28: curl gave up after its 3-second timeout. A flow opened in one
direction only allows replies in the other, never a new connection.

## 🎛️ Exercise 4: reach the API server under a closed egress

A Pod that talks to the API (an operator, a deployment tool) needs an egress
to it. Look at the two addresses of the API: the `kubernetes` Service's, and
the one really behind it:

```bash
kubectl get endpointslices -n default -l kubernetes.io/service-name=kubernetes -o jsonpath='{.items[0].endpoints[0].addresses[0]}:{.items[0].ports[0].port}{"\n"}'; kubectl get service kubernetes -n default -o jsonpath='{.spec.clusterIP}:{.spec.ports[0].port}{"\n"}'
```

```text
10.10.50.11:6443
10.96.0.1:443
```

The Service answers on `10.96.0.1:443`, but the API server listens on
`10.10.50.11:6443`, the control plane's address. Open egress to that address,
on the Service's port 443, and test:

```bash
API=$(kubectl get endpointslices -n default -l kubernetes.io/service-name=kubernetes -o jsonpath='{.items[0].endpoints[0].addresses[0]}'); cat <<YAML | kubectl apply -n essai-zc -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vers-api
spec:
  podSelector:
    matchLabels: {app: comptoir}
  policyTypes: [Egress]
  egress:
    - to:
        - ipBlock: {cidr: $API/32}
      ports:
        - {protocol: TCP, port: 443}
YAML
sleep 5; kubectl exec comptoir -n essai-zc -- nc -z -w 3 kubernetes.default 443; echo "port 443 : code $?"
```

```text
networkpolicy.networking.k8s.io/vers-api created
command terminated with exit code 1
port 443 : code 1
```

Denied. The Service's address and port are replaced by the API server's
before the policy is checked: Calico sees port 6443, not 443. Fix the rule's
port (`autorisé` means "allowed"):

```bash
kubectl patch networkpolicy vers-api -n essai-zc --type json -p '[{"op":"replace","path":"/spec/egress/0/ports/0/port","value":6443}]'; sleep 5; kubectl exec comptoir -n essai-zc -- nc -z -w 3 kubernetes.default 443; echo "port 6443 autorisé : code $?"
```

```text
networkpolicy.networking.k8s.io/vers-api patched
port 6443 autorisé : code 0
```

The client still calls `kubernetes.default` on port 443, but the rule must
name port 6443. A rule towards the API is read from the `kubernetes`
Service's EndpointSlice, not from the Service.

## 🏷️ Exercise 5: a removed label cuts the access

Remove the `app` label from `comptoir` (the final `-` deletes the label),
then call `caisse` again:

```bash
kubectl label pod comptoir -n essai-zc app-; sleep 5; kubectl exec comptoir -n essai-zc -- wget -qO- -T 3 http://caisse >/dev/null; echo "code $?"
```

```text
pod/comptoir unlabeled
wget: download timed out
command terminated with exit code 1
code 1
```

Both policies from exercise 3 targeted `app=comptoir`. Without the label,
`comptoir` only gets the full lockdown, which targets every Pod. In a
zero-trust namespace, labels are part of the security rules: changing them
changes the accesses.

## 🧹 Clean-up

Delete the two scratch namespaces:

```bash
kubectl delete namespace essai-zc essai-dehors
```

```text
namespace "essai-zc" deleted
namespace "essai-dehors" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-networkpolicy-default-deny
dsoxlab check cks-networkpolicy-default-deny
```

```text
╭─ Result: cks-networkpolicy-default-deny ─╮
│  0 / 100 pts                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests         │
╰──────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a namespace to close entirely, then reopen
for the one useful flow, without breaking name resolution.

```bash
dsoxlab run cks-networkpolicy-default-deny
dsoxlab challenge cks-networkpolicy-default-deny
```
