# Announce a Service over BGP

The lesson enables Cilium's BGP control plane, brings up the sessions with a
router and announces the Pod network and the LoadBalancer addresses to it.
That is also the challenge of this lab: this course leaves BGP off. It works
on the half of the subject that is set without it, the allocation of
LoadBalancer addresses by Cilium (LB IPAM): what an agent says when BGP is
off, an allocated address announced to nobody, a pool that runs out, an
address shared by two Services, and an address requested outside the pool.

You work in the `essai-bgp` namespace, with a scratch pool `172.31.0.0/30`
reserved for that namespace. The challenge uses another pool, another Service
and the BGP sessions: you will do it on your own, at the end.

Related page: [Announce Services over BGP](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/announce-services-bgp/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-annoncer-un-service-en-bgp
```

You are now connected to `net-cp.lab`, the control plane of the Cilium
cluster. The lab router runs outside the cluster; you do not touch it in this
course.

The outputs shown in this course were captured on these machines on
22 November 2026 (Kubernetes v1.37.2, Cilium 1.20.5).

## 🔌 Exercise 1: what an agent says when BGP is off

Before looking for why a router does not see the cluster, check that the
cluster speaks BGP. Ask an agent, the Cilium configuration, then port 179,
the BGP port, on a worker:

```bash
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg bgp peers; echo "code=$?"
kubectl -n kube-system get cm cilium-config -o yaml | grep -c bgp
ssh net-w1.lab 'sudo ss -ltn "sport = :179"'
```

```text
BGP Control Plane is disabled
code=0
0
State Recv-Q Send-Q Local Address:Port Peer Address:PortProcess
```

The agent answers `BGP Control Plane is disabled`, but exits with **0**: a
script that only looks at the exit code would believe everything is fine.
The Cilium configuration does not contain a single line about BGP, and
nobody listens on port 179 of the worker. A router that tries to reach these
nodes therefore stays `Active`, without ever getting a session.

## 🏷️ Exercise 2: an allocated address is not an announced address

LB IPAM allocates LoadBalancer addresses, even when BGP is off. Create a
scratch pool limited to the `essai-bgp` namespace by its `serviceSelector`,
then an application and a LoadBalancer Service:

```bash
kubectl create namespace essai-bgp; cat <<'YAML' | kubectl apply -f -
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: essai-pool
spec:
  allowFirstLastIPs: "No"
  blocks:
    - cidr: 172.31.0.0/30
  serviceSelector:
    matchLabels:
      io.kubernetes.service.namespace: essai-bgp
YAML
kubectl -n essai-bgp create deployment essai-web --image=nginx:1.30.6 --replicas=1
kubectl -n essai-bgp expose deployment essai-web --name=essai-a --type=LoadBalancer --port 80
kubectl -n essai-bgp rollout status deployment essai-web --timeout=120s
sleep 5; kubectl -n essai-bgp get svc essai-a
```

```text
namespace/essai-bgp created
ciliumloadbalancerippool.cilium.io/essai-pool created
deployment.apps/essai-web created
service/essai-a exposed
Waiting for deployment "essai-web" rollout to finish: 0 of 1 updated replicas are available...
deployment "essai-web" successfully rolled out
NAME      TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
essai-a   LoadBalancer   10.100.225.168   172.31.0.1    80:32739/TCP   6s
```

The Service got `172.31.0.1`. The `serviceSelector` matters: without it, the
pool would also serve the challenge's `web` Service, which is still waiting
for its address. Now call that address from `net-cp`, and look at the route
the kernel picks for it:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://172.31.0.1/
ip route get 172.31.0.1
```

```text
200
172.31.0.1 via 10.10.50.1 dev enp1s0 src 10.10.50.14 uid 1001
    cache
```

The address answers `200`, and yet the kernel would send it to the gateway
`10.10.50.1`, which does not know it. On a cluster node, Cilium intercepts the
call and serves it itself, before any route. **A test run from a node
therefore proves nothing about the announcement**: only a call from a machine
outside the cluster, like the router of the challenge, proves it. The
`sleep 5` is not decoration: in a first attempt, the same `curl`, run one
second after the Service was created, failed. Give Cilium a few seconds
before concluding that an address does not answer.

## 🔢 Exercise 3: a pool that runs out

The `/30` block holds four addresses, and the pool carries
`allowFirstLastIPs: "No"`, which reserves the first and the last. Create two
more Services on the same application:

```bash
kubectl -n essai-bgp expose deployment essai-web --name=essai-b --type=LoadBalancer --port 81 --target-port 80
kubectl -n essai-bgp expose deployment essai-web --name=essai-c --type=LoadBalancer --port 82 --target-port 80
sleep 5; kubectl -n essai-bgp get svc
kubectl -n essai-bgp get svc essai-c -o jsonpath='{range .status.conditions[*]}{.type}={.status} {.reason}: {.message}{"\n"}{end}'
```

```text
service/essai-b exposed
service/essai-c exposed
NAME      TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
essai-a   LoadBalancer   10.100.225.168   172.31.0.1    80:32739/TCP   11s
essai-b   LoadBalancer   10.109.116.46    172.31.0.2    81:30162/TCP   5s
essai-c   LoadBalancer   10.109.134.36    <pending>     82:30848/TCP   5s
cilium.io/IPAMRequestSatisfied=False out_of_ips: All enabled CiliumLoadBalancerIPPools that match this service ran out of allocatable IPs
```

The pool only gave `172.31.0.1` and `172.31.0.2`: `172.31.0.0` and
`172.31.0.3` are indeed reserved by `allowFirstLastIPs: "No"`. The third
Service stays `<pending>`, and the reason is not in the events but in the
**conditions** of the Service: `out_of_ips`.

## 🤝 Exercise 4: two Services on one address

When addresses are scarce, two Services can share one, as long as they listen
on different ports. The `lbipam.cilium.io/sharing-key` annotation ties them
together. Free the pending Service, give `essai-a` a key, then create a
Service that carries the same key, on port 8080:

```bash
kubectl -n essai-bgp delete svc essai-c
kubectl -n essai-bgp annotate svc essai-a lbipam.cilium.io/sharing-key=vitrine
cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: essai-d
  namespace: essai-bgp
  annotations:
    lbipam.cilium.io/sharing-key: vitrine
spec:
  type: LoadBalancer
  selector:
    app: essai-web
  ports:
    - port: 8080
      targetPort: 80
YAML
sleep 5; kubectl -n essai-bgp get svc
curl -s -o /dev/null -w '%{http_code}\n' http://172.31.0.1:8080/
```

```text
service "essai-c" deleted from essai-bgp namespace
service/essai-a annotated
service/essai-d created
NAME      TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)          AGE
essai-a   LoadBalancer   10.100.225.168   172.31.0.1    80:32739/TCP     16s
essai-b   LoadBalancer   10.109.116.46    172.31.0.2    81:30162/TCP     10s
essai-d   LoadBalancer   10.104.163.211   172.31.0.1    8080:32018/TCP   5s
200
```

`essai-d` got `172.31.0.1`, the address of `essai-a`, while the pool was
full: sharing does not use up an address. The application answers on port
8080 of that address, as on port 80.

## 🎯 Exercise 5: an address requested outside the pool

A Service can ask for a specific address with the `lbipam.cilium.io/ips`
annotation. Ask for `172.31.0.9`, which is in no pool:

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: essai-e
  namespace: essai-bgp
  annotations:
    lbipam.cilium.io/ips: 172.31.0.9
spec:
  type: LoadBalancer
  selector:
    app: essai-web
  ports:
    - port: 83
      targetPort: 80
YAML
sleep 5; kubectl -n essai-bgp get svc essai-e
kubectl -n essai-bgp get svc essai-e -o jsonpath='{range .status.conditions[*]}{.type}={.status} {.reason}: {.message}{"\n"}{end}'
```

```text
service/essai-e created
NAME      TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
essai-e   LoadBalancer   10.108.211.50   <pending>     83:31638/TCP   5s
cilium.io/IPAMRequestSatisfied=False no_pool: No pool exists with a CIDR containing '172.31.0.9'
```

Same symptom as in exercise 3, `<pending>`, but another reason: `no_pool`,
and the message names the requested address. In front of a `<pending>`
Service, always read its conditions before touching the pool.

## 🧹 Clean-up

Delete the scratch namespace, then the pool, which is attached to no
namespace. Check that the challenge's Service is still waiting for its
address:

```bash
kubectl delete namespace essai-bgp --wait=true --timeout=120s
kubectl delete ciliumloadbalancerippool essai-pool
kubectl -n bgp-demo get svc web
```

```text
namespace "essai-bgp" deleted
ciliumloadbalancerippool.cilium.io "essai-pool" deleted
NAME   TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
web    LoadBalancer   10.98.192.205   <pending>     80:31147/TCP   3m28s
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the
clean-up and then the lab preparation: you get back exactly the starting state
of the challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-annoncer-un-service-en-bgp
dsoxlab check k8s-annoncer-un-service-en-bgp
```

```text
╭─ Result: k8s-annoncer-un-service-en-bgp ─╮
│  0 / 100 pts                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests         │
╰──────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: enable BGP in Cilium, bring up the sessions
with the network router, and announce the Pod network and the address of the
`web` Service to it.

```bash
dsoxlab run k8s-annoncer-un-service-en-bgp
dsoxlab challenge k8s-annoncer-un-service-en-bgp
```
