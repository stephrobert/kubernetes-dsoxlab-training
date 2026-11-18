# Serve a Gateway and filter at L7 with Cilium

## The situation

The Cilium cluster of the `net-*` hosts has **three nodes**: `net-cp.lab`,
`net-w1.lab`, `net-w2.lab`. Cilium 1.20.5 replaces kube-proxy. Its **Gateway
API is turned off**, the Gateway API CRDs are not installed, and the cluster
has **no load balancer**.

In the namespace **`catalogue`**, the application **`fiches`** answers HTTP
behind the Service `fiches` (port 80). The Pod **`lecteur`** (label
`app: lecteur`) reads it. The team wants `fiches` published under the name
**`fiches.formation.test`** through a Gateway served by Cilium, and in
read-only mode: GET yes, writing no. For exposed addresses, the network team
gives you **`172.30.16.0/28`**.

You are on `net-cp.lab`, with `kubectl` and `helm` configured.

## What you must achieve

1. A **Gateway** of class `cilium` in `catalogue`, with an **HTTP listener on
   port 80**, is **Programmed** and has an address.
2. `http://fiches.formation.test/` through that Gateway reaches `fiches`.
3. From `lecteur`, `GET /` is served and `POST /` is **refused with a 403**.
4. Through the Gateway **too**, `GET /` is served and `POST /` is refused
   with a 403.

## The method, step by step

**Turn Cilium's Gateway API on.** Cilium 1.20.5 requires the Gateway API CRDs
**v1.6.3**: `kubectl apply --server-side -f
https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.3/standard-install.yaml`.
Then `helm upgrade cilium cilium/cilium --version 1.20.5 -n kube-system
--reuse-values --set gatewayAPI.enabled=true`, wait for the agents and
restart the operator. The GatewayClass **`cilium`** appears, `Accepted`.

**Serve fiches.** A `Gateway` with `gatewayClassName: cilium` and a listener
`HTTP` on port 80, and an `HTTPRoute` attached to it (`parentRefs`), limited
to the name (`hostnames`), towards the Service `fiches`. Cilium creates a
Service of type `LoadBalancer` for the Gateway: without a load balancer, the
Gateway stays **not Programmed**, reason `AddressNotAssigned`. A
**`CiliumLoadBalancerIPPool`** with the block `172.30.16.0/28` lets Cilium
give it an address. Check with `curl -H 'Host: fiches.formation.test'
http://<address>/` from `net-cp`.

**Filter at L7.** A **`CiliumNetworkPolicy`** on the Pods of `fiches` allows
`lecteur` (`fromEndpoints`) on port 5678, with `rules.http`: method `GET`,
path `/`. Cilium then sends this traffic through its proxy: a `POST` gets a
**403 Access denied**.

**Mind the Gateway.** As soon as the policy applies, the Gateway stops
answering: its traffic does not come from `lecteur`, it arrives with
Cilium's **reserved identity `ingress`**. Add an ingress rule with
`fromEntities: [ingress]` and the same `http` rules. The Gateway answers
again, and its `POST` is refused too.

## How you will know it works

The tests read the Gateway's conditions, then send real requests: through
the Gateway, and from `lecteur`, GET and POST each time.

```bash
dsoxlab check k8s-filtrer-en-l7-avec-cilium
```
