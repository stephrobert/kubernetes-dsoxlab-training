# Issue certificates with cert-manager and an internal CA

Guided lab of the "cert-manager" lesson, Administer the cluster module of
level 4: a self-signed issuer, an internal CA, a service certificate signed by
it, then a broken certificate to diagnose and repair. cert-manager v1.21.3,
installed and removed by the lab; public ACME out of the lab.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab sets up cert-manager and the `atelier-tls` namespace |
| Duration | about 35 minutes |
| Related page | [cert-manager, Put into practice section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cert-manager/#mettre-en-pratique) (in French) |

```bash
dsoxlab run   k8s-emettre-un-certificat-avec-cert-manager
dsoxlab check k8s-emettre-un-certificat-avec-cert-manager
```
