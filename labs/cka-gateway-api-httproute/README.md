# Route with the Gateway API, and see the Gateway declare itself programmed

**CKA** lab, *Services and Networking* domain (20 % of the exam), competency
"Use the Gateway API to manage Ingress traffic".

Twin of [`cka-ingress-path-routing`](../cka-ingress-path-routing/): same
starting situation, same proof, and the other way of routing it. Playing them
one after the other shows what the Gateway API changes, and what it does not.

**The trap specific to this API is measured and makes the first test.** A
Gateway whose listener declares a port matching none of the controller's entry
points is **accepted** by the API, shows up in `kubectl get`, and is **never
programmed**: nothing routes, and nothing says so but its conditions. The test
therefore reads `Programmed`, not the object's existence.

That is also why `shared/traefik.yml` aligns the web entrypoint on port **80**
with the `net.ipv4.ip_unprivileged_port_start=0` sysctl: the chart puts it on
8000, and a candidate writing `port: 80`, which every piece of documentation
shows them, would see their Gateway stay silent.

Measured on 2026-09-16, `Programmed=True` and:

| path | answer |
|---|---|
| `/api` | `api` |
| `/web` | `web` |
| `/autre` | 404 |

Both applications answer with their own name, using
`hashicorp/http-echo:1.0.0`: the inherited lab served `nginx:1.27` on both
sides and could therefore not tell a reversed routing from a correct one.

Gateway API CRDs **v1.6.2**, `standard` channel, placed by the setup and not by
the chart, which warns it will stop shipping them.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 25 minutes |
| Companion lesson | [Gateway API](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/gateway-api/) |

```bash
dsoxlab run   cka-gateway-api-httproute
dsoxlab check cka-gateway-api-httproute
```

The `cleanup.yaml` takes back the CRDs **and** the
`safe-upgrades.gateway.networking.k8s.io` ValidatingAdmissionPolicy that
`standard-install.yaml` also places: these are cluster-scoped objects, and no
`delete crd` takes it back.
