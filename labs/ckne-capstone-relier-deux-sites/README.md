# Capstone: link two sites, announce a Service to the network and serve it over HTTPS

Capstone of the **CKNE** certification in the Kubernetes course (level 6), in
the CKNE timed exercises page. It names no object: link two sites so the shop
answers from both and survives the loss of one, announce it over BGP to the
network team's router, and serve it over HTTPS under its public name with a
cert-manager certificate, plain HTTP being redirected. Three requirements, all
blocking, pass mark 70.

| | |
|---|---|
| Target | `ha-cp1.lab` (site 1) and `ha-cp2.lab` (site 2), two single-node Cilium 1.20.5 clusters without kube-proxy; the network team's FRR 10.6.2 router on `k8s-cp.lab` |
| Duration | about 75 minutes |
| Related page | [CKNE timed exercises](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/certifications/ckne/exercises/) |

```bash
dsoxlab run    ckne-capstone-relier-deux-sites
dsoxlab check  ckne-capstone-relier-deux-sites
dsoxlab submit ckne-capstone-relier-deux-sites
```
