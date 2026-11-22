# Observe flows with Hubble

The lesson uses Hubble to find a refused flow, count it and log it. This
course uses Hubble on **accepted** flows, for what the lesson does not show:
following a connection seen by two agents, querying the whole cluster at once
through the relay, making the DNS names a Pod asks for visible, reading the
DNS metrics, and translating `hubble observe` options into a JSON filter.

You work in the `essai-hubble` namespace, with a web server and a probe that
calls it every 5 seconds. The challenge uses another namespace, other Pods and
refused flows: you will do it on your own, at the end.

Related page: [Observe, measure and audit flows with Hubble](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/hubble/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-auditer-les-flux-avec-hubble
```

You are now connected to `net-cp.lab`, the control plane of the Cilium
cluster. Create the scratch objects: an nginx server on `net-w1`, its
Service, and a probe on `net-w2` that calls it in a loop.

```bash
kubectl create namespace essai-hubble; cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: serveur
  namespace: essai-hubble
  labels:
    app: serveur
spec:
  nodeName: net-w1.lab
  containers:
    - name: web
      image: nginx:1.30.6
---
apiVersion: v1
kind: Service
metadata:
  name: serveur
  namespace: essai-hubble
spec:
  selector:
    app: serveur
  ports:
    - port: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: sonde
  namespace: essai-hubble
spec:
  nodeName: net-w2.lab
  containers:
    - name: client
      image: busybox:1.38.0
      command: ["sh", "-c", "while true; do wget -q -O /dev/null 'http://serveur'; sleep 5; done"]
YAML
kubectl -n essai-hubble wait --for=condition=Ready pod/serveur pod/sonde --timeout=120s
```

```text
namespace/essai-hubble created
pod/serveur created
service/serveur created
pod/sonde created
pod/serveur condition met
pod/sonde condition met
```

The outputs shown in this course were captured on these machines on
22 November 2026 (Kubernetes v1.37.2, Cilium 1.20.5).

## 🔭 Exercise 1: one connection, seen by two agents

Each Cilium agent only sees the flows of the Pods on its node. A connection
between two nodes is therefore seen twice. Find the agent of each worker,
then ask both for the same connection, from the probe to the server:

```bash
w1=$(kubectl -n kube-system get pods -l k8s-app=cilium --field-selector spec.nodeName=net-w1.lab -o name)
w2=$(kubectl -n kube-system get pods -l k8s-app=cilium --field-selector spec.nodeName=net-w2.lab -o name)
kubectl -n kube-system exec $w2 -c cilium-agent -- hubble observe --from-pod essai-hubble/sonde --to-pod essai-hubble/serveur --last 4
kubectl -n kube-system exec $w1 -c cilium-agent -- hubble observe --from-pod essai-hubble/sonde --to-pod essai-hubble/serveur --last 4
```

```text
Nov 22 22:11:47.896: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: SYN)
Nov 22 22:11:47.897: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: ACK)
Nov 22 22:11:47.897: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: ACK, PSH)
Nov 22 22:11:47.898: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: ACK, FIN)
Nov 22 22:11:47.903: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-endpoint FORWARDED (TCP Flags: SYN)
Nov 22 22:11:47.904: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-endpoint FORWARDED (TCP Flags: ACK)
Nov 22 22:11:47.904: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-endpoint FORWARDED (TCP Flags: ACK, PSH)
Nov 22 22:11:47.905: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-endpoint FORWARDED (TCP Flags: ACK, FIN)
```

The first four lines come from the `net-w2` agent, the next four from the
`net-w1` agent. The source port, `44604`, is the same: it is the same
connection, from `SYN` to `FIN`. What changes is the **observation point**.
On `net-w2`, the packet leaves `to-overlay`, towards the tunnel that links
the nodes. On `net-w1`, it arrives `to-endpoint`, delivered to the server Pod.
The Service shows up nowhere: Cilium has already replaced its address with
the Pod's.

## 🛰️ Exercise 2: the whole cluster at once, through the relay

The Hubble relay gathers the flows of every agent. The agent's `hubble`
binary can query it with `--server`. The relay has a Service address, which
you read before calling it:

```bash
relais=$(kubectl -n kube-system get svc hubble-relay -o jsonpath='{.spec.clusterIP}')
kubectl -n kube-system exec $w1 -c cilium-agent -- hubble observe --server $relais:80 --namespace essai-hubble --last 2
```

```text
Nov 22 22:11:47.898: essai-hubble/sonde:44604 (ID:15653) <- essai-hubble/serveur:80 (ID:14478) to-endpoint FORWARDED (TCP Flags: ACK, FIN, PSH)
Nov 22 22:11:47.898: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: ACK, FIN)
Nov 22 22:11:47.901: essai-hubble/sonde:37889 (ID:15653) -> kube-system/coredns-559f6c778d-hzktv:53 (ID:19510) to-endpoint FORWARDED (UDP)
Nov 22 22:11:47.902: essai-hubble/sonde:37889 (ID:15653) <- kube-system/coredns-559f6c778d-hzktv:53 (ID:19510) to-overlay FORWARDED (UDP)
Nov 22 22:11:47.905: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-endpoint FORWARDED (TCP Flags: ACK, FIN)
Nov 22 22:11:47.905: essai-hubble/sonde:44604 (ID:15653) <- essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: ACK)
```

You asked for 2 flows and you get 6: the relay applies `--last` **to each
node**, then sorts the answers by time. The two DNS lines come from the node
that runs this CoreDNS Pod. The relay also shows the return direction (`<-`)
that exercise 1 filtered out. It is the right tool when you do not know yet
which node to look at. Keep this per-node `--last` in mind when you limit an
output.

## 🏷️ Exercise 3: see the DNS names a Pod asks for

Ask the `net-w2` agent for the probe's DNS flows, then for its UDP flows to
port 53:

```bash
kubectl -n kube-system exec $w2 -c cilium-agent -- hubble observe --pod essai-hubble/sonde --protocol dns --last 2
kubectl -n kube-system exec $w2 -c cilium-agent -- hubble observe --pod essai-hubble/sonde --protocol udp --to-port 53 --last 1
```

```text
Nov 22 22:11:47.895: essai-hubble/sonde:37889 (ID:15653) -> kube-system/coredns-559f6c778d-hzktv:53 (ID:19510) to-overlay FORWARDED (UDP)
```

The `--protocol dns` filter returns nothing, while the probe queries CoreDNS
every 5 seconds: the second command proves it. Hubble sees UDP packets, not
DNS questions. To read the names, Cilium must send the Pod's DNS through its
proxy, and a DNS rule in a CiliumNetworkPolicy triggers that. Apply a policy
that allows any name (`matchPattern: "*"`) towards CoreDNS, and any traffic
towards the Pods of the namespace:

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: voir-le-dns
  namespace: essai-hubble
spec:
  endpointSelector:
    matchLabels: {}
  egress:
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: kube-system
            k8s-app: kube-dns
      toPorts:
        - ports:
            - port: "53"
              protocol: ANY
          rules:
            dns:
              - matchPattern: "*"
    - toEndpoints:
        - {}
YAML
sleep 15
kubectl -n kube-system exec $w2 -c cilium-agent -- hubble observe --pod essai-hubble/sonde --protocol dns --last 4
kubectl -n kube-system exec $w2 -c cilium-agent -- hubble observe --from-pod essai-hubble/sonde --to-pod essai-hubble/serveur --last 1
```

```text
ciliumnetworkpolicy.cilium.io/voir-le-dns created
Nov 22 22:12:02.915: essai-hubble/sonde:44697 (ID:15653) -> kube-system/coredns-559f6c778d-mql8q:53 (ID:19510) dns-request proxy FORWARDED (DNS Query serveur.essai-hubble.svc.cluster.local. AAAA)
Nov 22 22:12:02.915: essai-hubble/sonde:44697 (ID:15653) -> kube-system/coredns-559f6c778d-mql8q:53 (ID:19510) dns-request proxy FORWARDED (DNS Query serveur.essai-hubble.svc.cluster.local. A)
Nov 22 22:12:02.916: essai-hubble/sonde:44697 (ID:15653) <- kube-system/coredns-559f6c778d-mql8q:53 (ID:19510) dns-response proxy FORWARDED (DNS Answer  TTL: 4294967295 (Proxy serveur.essai-hubble.svc.cluster.local. AAAA))
Nov 22 22:12:02.916: essai-hubble/sonde:44697 (ID:15653) <- kube-system/coredns-559f6c778d-mql8q:53 (ID:19510) dns-response proxy FORWARDED (DNS Answer "10.110.210.236" TTL: 30 (Proxy serveur.essai-hubble.svc.cluster.local. A))
Nov 22 22:12:02.918: essai-hubble/sonde:41190 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: ACK, FIN)
```

The flows now carry `dns-request proxy` and `dns-response proxy`: the name
asked for, `serveur.essai-hubble.svc.cluster.local.`, the type (`A` for IPv4,
`AAAA` for IPv6) and the answer, the address of the Service. The `AAAA`
question comes back without an address: the Service has no IPv6 address. The
last line shows that the probe still reaches its server. That is the job of
the second rule: an egress policy refuses everything it does not mention,
and without that rule the traffic to the server would no longer be allowed.

## 📈 Exercise 4: the DNS metrics of the node

The cluster enables Hubble's `dns` metrics family. Its counters only move for
DNS that goes through the proxy, so since exercise 3. Read them on port 9965
of `net-w2` (`10.10.50.16`, given by `kubectl get node net-w2.lab -o wide`):

```bash
curl -s http://10.10.50.16:9965/metrics | grep -E '^hubble_dns_(queries|responses)_total'
```

```text
hubble_dns_queries_total{ips_returned="0",qtypes="A",rcode=""} 16
hubble_dns_queries_total{ips_returned="0",qtypes="AAAA",rcode=""} 16
hubble_dns_responses_total{ips_returned="0",qtypes="AAAA",rcode="No Error"} 16
hubble_dns_responses_total{ips_returned="1",qtypes="A",rcode="No Error"} 16
```

Questions and answers are counted separately. Answers carry the return code
(`rcode`) and the number of addresses returned: an `A` answer returns one
address, an `AAAA` answer none, and both say `No Error`. An `rcode` label
other than `No Error` points to names that do not resolve. This counter
belongs to the agent, not to the namespace: it adds up all the DNS that went
through the proxy of this node since the agent started. Compare two readings
rather than a single value.

## 🧩 Exercise 5: translate options into a JSON filter

Hubble's export and its settings are described with JSON filters, not with
command-line options. `--print-raw-filters` gives the translation of a
command without reading anything:

```bash
kubectl -n kube-system exec $w2 -c cilium-agent -- hubble observe --pod essai-hubble/sonde --protocol dns --print-raw-filters
```

```text
allowlist:
    - '{"source_pod":["essai-hubble/sonde"],"protocol":["dns"]}'
    - '{"destination_pod":["essai-hubble/sonde"],"protocol":["dns"]}'
```

The `--pod` option becomes **two** filters, one for each direction: the probe
as source, then as destination. Inside each filter, the two fields combine
(AND), and the two filters add up (OR). This is the safest way to write a
JSON filter: start from the command that already shows the right flows, and
copy its translation.

## 🧹 Clean-up

Delete the scratch namespace. The CiliumNetworkPolicy, attached to the
namespace, goes with it:

```bash
kubectl delete namespace essai-hubble --wait=true --timeout=120s
```

```text
namespace "essai-hubble" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the
clean-up and then the lab preparation: you get back exactly the starting state
of the challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-auditer-les-flux-avec-hubble
dsoxlab check k8s-auditer-les-flux-avec-hubble
```

```text
╭─ Result: k8s-auditer-les-flux-avec-hubble ─╮
│  0 / 100 pts                               │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests           │
╰────────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a client of an API no longer gets an
answer. Find it with Hubble without lifting the policy, count its refusals
and keep a trace of them on the node.

```bash
dsoxlab run k8s-auditer-les-flux-avec-hubble
dsoxlab challenge k8s-auditer-les-flux-avec-hubble
```
