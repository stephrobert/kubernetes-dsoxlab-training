# Restore the cluster's DNS resolution

The lesson shows how Pods find Services by name: the Pod's
`/etc/resolv.conf` file, CoreDNS and its configuration, the Corefile. This
course has you run your own scratch CoreDNS next to the cluster's, and shows
cases the lesson does not: a Pod that chooses its DNS server, a name rewritten
by CoreDNS, a zone sent to a server that never answers, a Service that is only
an alias, and a Pod that uses the node's DNS instead of the cluster's.

You work in a scratch namespace, `essai-dns`, with a server `vitrine` (nginx)
and client Pods (busybox). The challenge is about other objects: you will do
it on your own, at the end.

Related page: [CoreDNS](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/coredns/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-troubleshoot-dns
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The lab broke the cluster's DNS: that is the challenge. This course does not
touch it. It runs its own CoreDNS in the scratch namespace.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2, CoreDNS 1.14.6 and busybox 1.38.

## 🔍 Exercise 1: see that the cluster's DNS does not answer

Create the namespace, a server exposed by a Service, and a client Pod:

```bash
kubectl create namespace essai-dns
kubectl run vitrine --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-dns --labels=app=vitrine; kubectl expose pod vitrine --port=80 -n essai-dns; kubectl wait --for=condition=Ready pod/vitrine -n essai-dns --timeout=120s
kubectl run poste --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-dns -- sleep 3600; kubectl wait --for=condition=Ready pod/poste -n essai-dns --timeout=120s
```

```text
namespace/essai-dns created
pod/vitrine created
service/vitrine exposed
pod/vitrine condition met
pod/poste created
pod/poste condition met
```

Ask the client for the Service's full name:

```bash
kubectl exec poste -n essai-dns -- nslookup -timeout=3 vitrine.essai-dns.svc.cluster.local; echo "code $?"
```

```text
;; connection timed out; no servers could be reached

nslookup: write to '10.96.0.10': Connection refused
command terminated with exit code 1
code 1
```

The client sent its question to `10.96.0.10`, the address of the cluster's DNS
Service, and it was refused. The `vitrine` Service does exist: it is the DNS
that does not answer. Why it does not answer is the challenge. For the rest of
the course, you run your own DNS server.

## 🧰 Exercise 2: a scratch CoreDNS, with the cluster's permissions

CoreDNS reads Services and Pods from the API to answer. Look at the image the
cluster uses and at its role's permissions:

```bash
kubectl -n kube-system get deployment coredns -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'; kubectl get clusterrole system:coredns -o jsonpath='{range .rules[*]}{.resources}{" "}{.verbs}{"\n"}{end}'
```

```text
registry.k8s.io/coredns/coredns:v1.14.6
["endpoints","services","pods","namespaces"] ["list","watch"]
["endpointslices"] ["list","watch"]
```

The `system:coredns` role allows listing and watching (`list`, `watch`)
Services, Pods, namespaces and EndpointSlices. Nothing else: CoreDNS never
changes the API.

Now run your scratch CoreDNS. The command creates a ServiceAccount bound to
that role, writes a Corefile, stores it in a ConfigMap, then starts a
Deployment with the same image as the cluster and exposes it over UDP on port
53:

```bash
IMG=$(kubectl -n kube-system get deployment coredns -o jsonpath='{.spec.template.spec.containers[0].image}'); kubectl create serviceaccount dns-essai -n essai-dns; kubectl create clusterrolebinding essai-dns --clusterrole=system:coredns --serviceaccount=essai-dns:dns-essai; cat > ~/Corefile.essai <<'COREFILE'
.:53 {
    errors
    rewrite name exact catalogue.local vitrine.essai-dns.svc.cluster.local
    kubernetes cluster.local in-addr.arpa ip6.arpa {
       pods insecure
       fallthrough in-addr.arpa ip6.arpa
    }
    cache 30
}
essai.test:53 {
    errors
    forward . 192.0.2.53
}
COREFILE
kubectl create configmap dns-essai -n essai-dns --from-file=Corefile=$HOME/Corefile.essai
cat <<YAML | kubectl apply -n essai-dns -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dns-essai
spec:
  replicas: 1
  selector:
    matchLabels: {app: dns-essai}
  template:
    metadata:
      labels: {app: dns-essai}
    spec:
      serviceAccountName: dns-essai
      containers:
        - name: coredns
          image: $IMG
          args: ["-conf", "/etc/coredns/Corefile"]
          securityContext:
            capabilities:
              add: [NET_BIND_SERVICE]
              drop: [ALL]
          volumeMounts:
            - {name: conf, mountPath: /etc/coredns}
      volumes:
        - name: conf
          configMap: {name: dns-essai}
YAML
kubectl expose deployment dns-essai -n essai-dns --port=53 --protocol=UDP; kubectl rollout status deployment/dns-essai -n essai-dns --timeout=120s
```

```text
serviceaccount/dns-essai created
clusterrolebinding.rbac.authorization.k8s.io/essai-dns created
configmap/dns-essai created
deployment.apps/dns-essai created
service/dns-essai exposed
Waiting for deployment "dns-essai" rollout to finish: 0 of 1 updated replicas are available...
deployment "dns-essai" successfully rolled out
```

The Corefile declares two blocks. The first one (`.:53`) answers everything:
it serves the `cluster.local` zone through the `kubernetes` plugin, and
rewrites one name with `rewrite`. The second one (`essai.test:53`) sends
everything ending in `essai.test` to another server, with `forward`.
Exercises 4 and 5 use them.

Read the start of the log:

```bash
sleep 3; kubectl logs deploy/dns-essai -n essai-dns | head -4
```

```text
maxprocs: Leaving GOMAXPROCS=2: CPU quota undefined
.:53
essai.test.:53
CoreDNS-1.14.6
```

CoreDNS lists the two blocks it serves, then its version. This is the first
thing to read when CoreDNS does not answer as expected: a block missing from
this list was not loaded.

## 🧭 Exercise 3: a Pod that chooses its DNS server

By default, a Pod uses the cluster's DNS. With `dnsPolicy: None`, you write
its `/etc/resolv.conf` yourself in the `dnsConfig` field. Create a Pod that
queries your scratch CoreDNS:

```bash
IP=$(kubectl get service dns-essai -n essai-dns -o jsonpath='{.spec.clusterIP}'); cat <<YAML | kubectl apply -n essai-dns -f -
apiVersion: v1
kind: Pod
metadata:
  name: guichet
spec:
  dnsPolicy: None
  dnsConfig:
    nameservers: ["$IP"]
    searches: [essai-dns.svc.cluster.local, svc.cluster.local, cluster.local]
    options:
      - {name: ndots, value: "5"}
  containers:
    - name: guichet
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "3600"]
YAML
kubectl wait --for=condition=Ready pod/guichet -n essai-dns --timeout=120s; kubectl exec guichet -n essai-dns -- cat /etc/resolv.conf
```

```text
pod/guichet created
pod/guichet condition met
search essai-dns.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.97.43.189
options ndots:5
```

The file holds exactly what you declared: the server, the search list
(`search`) and `ndots:5`. With `ndots:5`, a name with fewer than five dots is
first completed with each suffix of the list. Try a short name:

```bash
kubectl exec guichet -n essai-dns -- nslookup vitrine; kubectl exec guichet -n essai-dns -- wget -qO- -T 3 "http://vitrine" | grep -o '<title>.*</title>'
```

```text
Server:		10.97.43.189
Address:	10.97.43.189:53

** server can't find vitrine.cluster.local: NXDOMAIN

Name:	vitrine.essai-dns.svc.cluster.local
Address: 10.96.88.251

** server can't find vitrine.svc.cluster.local: NXDOMAIN

** server can't find vitrine.cluster.local: NXDOMAIN


** server can't find vitrine.svc.cluster.local: NXDOMAIN

command terminated with exit code 1
<title>Welcome to nginx!</title>
```

Read this output carefully. busybox's `nslookup` tries each suffix and prints
an `NXDOMAIN` for each failed attempt. In the middle, it finds
`vitrine.essai-dns.svc.cluster.local`. Yet it returns code 1 (`command
terminated with exit code 1`), because one of the attempts failed. The `wget`
right after proves that the short name works. With busybox, do not trust the
exit code of `nslookup`: read the `Name` line.

## ✏️ Exercise 4: a name rewritten by CoreDNS

The Corefile contains `rewrite name exact catalogue.local
vitrine.essai-dns.svc.cluster.local`. Query this name, which exists in no
zone:

```bash
kubectl exec guichet -n essai-dns -- nslookup catalogue.local; kubectl exec guichet -n essai-dns -- wget -qO- -T 3 "http://catalogue.local" | grep -o '<title>.*</title>'
```

```text
Server:		10.97.43.189
Address:	10.97.43.189:53

Name:	catalogue.local
Address: 10.96.88.251


<title>Welcome to nginx!</title>
```

CoreDNS replaced the name before looking it up, then returned the answer under
the requested name. The client does not see the rewrite. This is useful to
keep an old name during a migration. It is also a trap when troubleshooting: a
name that answers is not necessarily a name that exists. The Corefile is the
only way to know.

## ⏳ Exercise 5: a zone sent to a silent server

The `essai.test` block sends its questions to `192.0.2.53`, an address
reserved for documentation, which nothing serves. Query a name in that zone
and time it (`code 1 en 3 s` reads "code 1 in 3 s"):

```bash
kubectl exec guichet -n essai-dns -- sh -c 'debut=$(date +%s); nslookup -timeout=3 intranet.essai.test; echo "code $? en $(( $(date +%s) - debut )) s"'
```

```text
;; connection timed out; no servers could be reached

code 1 en 3 s
```

The client waits for its 3 seconds, then gives up. This is not an `NXDOMAIN`:
nobody answered. The CoreDNS log says why, a few seconds later:

```bash
sleep 8; kubectl logs deploy/dns-essai -n essai-dns --tail=3
```

```text
[ERROR] plugin/errors: 2 intranet.essai.test. AAAA: read udp 10.244.38.127:49120->192.0.2.53:53: i/o timeout
[ERROR] plugin/errors: 2 intranet.essai.test. A: read udp 10.244.38.127:39073->192.0.2.53:53: i/o timeout
[ERROR] plugin/errors: 2 intranet.essai.test. AAAA: read udp 10.244.38.127:54346->192.0.2.53:53: i/o timeout
```

`i/o timeout` to `192.0.2.53:53`: CoreDNS did receive the question and passed
it on, but the next server never answered. The `errors` plugin writes these
lines. Without it, the failure leaves no trace. The rest of the DNS still
works:

```bash
kubectl exec guichet -n essai-dns -- wget -qO- -T 3 "http://vitrine" | grep -o '<title>.*</title>'
```

```text
<title>Welcome to nginx!</title>
```

Remember the difference: `NXDOMAIN` means a server answered that the name does
not exist, a timeout means nobody answered.

## 🔗 Exercise 6: a Service that is only an alias

An `ExternalName` Service has neither an address nor an endpoint: it is a DNS
alias. Create one that points to `vitrine`:

```bash
kubectl create service externalname annuaire --external-name=vitrine.essai-dns.svc.cluster.local -n essai-dns; kubectl get service annuaire -n essai-dns
```

```text
service/annuaire created
NAME       TYPE           CLUSTER-IP   EXTERNAL-IP                           PORT(S)   AGE
annuaire   ExternalName   <none>       vitrine.essai-dns.svc.cluster.local   <none>    0s
```

No `CLUSTER-IP`, no port. Query it:

```bash
kubectl exec guichet -n essai-dns -- nslookup annuaire
```

```text
Server:		10.97.43.189
Address:	10.97.43.189:53

** server can't find annuaire.cluster.local: NXDOMAIN

annuaire.essai-dns.svc.cluster.local	canonical name = vitrine.essai-dns.svc.cluster.local
Name:	vitrine.essai-dns.svc.cluster.local
Address: 10.96.88.251

** server can't find annuaire.cluster.local: NXDOMAIN




command terminated with exit code 1
```

CoreDNS answers with a `canonical name` (a CNAME) to
`vitrine.essai-dns.svc.cluster.local`, then with that name's address. The same
busybox trap comes back: code 1 although the name is found. An `ExternalName`
Service therefore depends entirely on DNS: if the target name does not
resolve, the alias leads nowhere, and kube-proxy cannot help.

## 🏠 Exercise 7: dnsPolicy Default, the node's DNS

The name is misleading: `dnsPolicy: Default` is not the default value. The
default value is `ClusterFirst`. `Default` gives the Pod the node's DNS.
Create a Pod with this policy and read its `/etc/resolv.conf`:

```bash
kubectl run noeud-dns --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-dns --overrides='{"spec":{"dnsPolicy":"Default"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/noeud-dns -n essai-dns --timeout=120s; kubectl exec noeud-dns -n essai-dns -- cat /etc/resolv.conf
```

```text
pod/noeud-dns created
pod/noeud-dns condition met
search lab
nameserver 10.10.50.1
```

The Pod received the node's file: the `lab` search domain and the server
`10.10.50.1`, the one of the machines' network. Ask it for a cluster name:

```bash
kubectl exec noeud-dns -n essai-dns -- nslookup -timeout=3 vitrine.essai-dns.svc.cluster.local; echo "code $?"
```

```text
;; connection timed out; no servers could be reached

command terminated with exit code 1
code 1
```

The node's server does not know `cluster.local`. A Pod that finds no Service
while its neighbours do deserves a look at its `dnsPolicy` field, before you
suspect CoreDNS.

## 🧹 Clean-up

Delete the scratch namespace, the role binding (it belongs to no namespace)
and the Corefile:

```bash
kubectl delete namespace essai-dns; kubectl delete clusterrolebinding essai-dns; rm -f ~/Corefile.essai
```

```text
namespace "essai-dns" deleted
clusterrolebinding.rbac.authorization.k8s.io "essai-dns" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-dns
dsoxlab check cka-troubleshoot-dns
```

```text
╭── Result: cka-troubleshoot-dns ───╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for
you, untouched.

## 🎯 The challenge

Your turn, on your own this time: the cluster's DNS no longer answers, find
out why and bring it back into service.

```bash
dsoxlab run cka-troubleshoot-dns
dsoxlab challenge cka-troubleshoot-dns
```
