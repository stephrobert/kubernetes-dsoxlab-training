# Serve a site over HTTPS with its own certificate, not the controller's

**CKS** lab, *Cluster Setup* domain (15 % of the exam), competency "Use
Ingress with TLS to secure application access".

The Ingress controller is installed by the setup: what the lab measures is TLS
termination, not installing a controller.

**The trap is measured, and it is what makes the lab.** With no TLS section at
all, the controller already answers **200 over HTTPS**, with a generic
self-signed certificate it builds at startup. A test settling for "the site
answers over HTTPS" would therefore be green **before** the work. What
distinguishes the two states is the certificate PRESENTED, read on the
connection itself:

| | Certificate served for `vitrine.lab` |
|---|---|
| before | `CN = TRAEFIK DEFAULT CERT` |
| after | `CN = vitrine.lab` |

No manifest reading would replace that measurement: a Secret can exist, be of
the right type, and be served to nobody because the Ingress does not declare
it.

**Traefik, not ingress-nginx**: the latter has been archived since 24 March
2026, and the blog lesson moved on. Chart `traefik/traefik` **41.6.0**,
appVersion v3.7.13, measured available on 2026-09-16, exposed on NodePort
30080 and 30443 because a LoadBalancer Service would stay `Pending` on a
kubeadm cluster with no cloud provider. Measured cost: about 66 MB.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 25 minutes |
| Companion lesson | [Ingress](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ingress/) |

```bash
dsoxlab run   cks-ingress-tls
dsoxlab check cks-ingress-tls
```

The `cleanup.yaml` uninstalls the release **and** deletes the CRDs: `helm
uninstall` deliberately leaves them behind, and they are cluster-scoped
objects the validator's snapshot would see appear.
