# Route two applications on a single host, and prove each gets its own

**CKA** lab, *Services and Networking* domain (20 % of the exam), Ingress
exposure.

**The inherited lab could prove nothing**, which is what drove its rewrite: it
served `nginx:1.27` on **both** sides. Its tests could therefore distinguish
neither a reversed routing nor the absence of routing. Here both applications
answer with their own name, using `hashicorp/http-echo:1.0.0`.

The test queries **three** paths, and the third is the control: a single rule
sending everything to one service would pass the first two measurements without
routing anything.

Measured on 2026-09-16:

| path | answer |
|---|---|
| `/api` | `api` |
| `/web` | `web` |
| `/autre` | 404 |

**Traefik, not ingress-nginx**: the latter has been archived since 24 March
2026, and the blog lesson moved on. Chart `traefik/traefik` **41.6.0**,
appVersion v3.7.13, exposed on NodePort because a LoadBalancer Service would
stay `Pending` on a kubeadm cluster with no cloud provider.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 20 minutes |
| Companion lesson | [Ingress](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ingress/) |

```bash
dsoxlab run   cka-ingress-path-routing
dsoxlab check cka-ingress-path-routing
```
