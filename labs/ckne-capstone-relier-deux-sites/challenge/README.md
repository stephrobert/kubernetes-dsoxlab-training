# Challenge: Capstone: link two sites, announce a Service to the network and serve it over HTTPS

## The situation

The shop runs on two sites, each in its own single-node Kubernetes 1.37
cluster, without kube-proxy, with Cilium 1.20.5:

| Site | Node | `kubectl` context |
|---|---|---|
| site 1 | `ha-cp1.lab` | `cluster-1` (current) |
| site 2 | `ha-cp2.lab` | `cluster-2` |

In each site, the namespace **`boutique`** holds the **shop** (`vitrine`),
which answers with the name of its site, behind an ordinary Service `vitrine`.
Today, each site only knows its own shop.

Both clusters were installed so they can be linked: distinct cluster
identifiers, the same certificate authority, and what Cilium needs. They are
not linked yet. The `cilium` CLI (v0.20.3) is installed on `ha-cp1.lab`.

On **site 1** only:

- the Pod **`client`** is there for your tests;
- the Service **`interne`**, of type LoadBalancer, is reserved for the
  operations team: it must **never** be announced to the network;
- the Cilium BGP control plane is on, the Gateway API (v1.6.3) is served by
  Cilium, and cert-manager (v1.21.3) has an internal authority, the
  ClusterIssuer **`autorite-des-sites`**.

The network team has a router outside the clusters, at **10.10.50.200**, in AS
**65000**. It expects site 1 as a neighbour, in AS **65001**. It reserves the
address block **`192.168.240.0/28`** for you. You cannot log into the router:
the tests will read it for you.

The public name of the shop is **`boutique.sites.test`**.

You work on `ha-cp1.lab`, with `kubectl` and `helm` configured and root through
`sudo`. No procedure is given, and no object is named: choosing the right ones
is part of the capstone.

## What you must achieve

1. From the site 1 client, the name `vitrine.boutique` answers from **both
   sites**. If site 1 has no shop replica left, the name still answers, from
   site 2.
2. The network team's router reaches the shop of **site 1** at an address of
   the reserved block, which it **learnt by itself**. The Service `interne` is
   not announced.
3. Clients reach the shop of site 1 at **`https://boutique.sites.test`**, with
   a certificate issued by **cert-manager** from the authority
   `autorite-des-sites`. A request over **HTTP** on that name is **redirected**
   to HTTPS, with a 301.

## How you will be graded

Three requirements, equally weighted, and all **blocking**: passing the other two
does not make up for missing one of them. The pass mark is **70 out of 100**.
The feedback is limited to the list of unmet criteria, by their label, and the
score: no message says why.

The tests read the clusters, never your files. They call the shop from the
client, empty site 1 of its replicas themselves then put them back, read the
router's table and call the shop from it, and verify the served certificate
with the sites' authority.

```bash
dsoxlab check  ckne-capstone-relier-deux-sites
dsoxlab submit ckne-capstone-relier-deux-sites
```
