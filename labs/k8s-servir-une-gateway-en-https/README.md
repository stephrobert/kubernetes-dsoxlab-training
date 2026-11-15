# Serve an Istio Gateway over HTTPS with a cert-manager certificate

Guided lab of the lesson "Serve a Gateway over HTTPS with cert-manager", level 6
"Advanced networking" of the Kubernetes course (CKNE objective "Managing TLS
Certificates for Gateway API"). Request a certificate from cert-manager in the
namespace of the Gateway, declare an Istio Gateway with an HTTPS listener that
presents it, attach a route, and prove the result with a real TLS client.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster, grown with the optional second worker `k8s-w2.lab`; the lab installs Istio 1.32 in ambient mode, the Gateway API v1.6.1 and cert-manager v1.21.3 |
| Duration | about 35 minutes |
| Prerequisite | the cert-manager lab `k8s-emettre-un-certificat-avec-cert-manager` (level 4) |
| Related page | [Kubernetes course](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/), until the lesson is published |

The `run` of this lab mounts `k8s-w2.lab` if it is not running yet, and joins it
to the cluster. The `cleanup.yaml` deletes the namespace `vitrine`, removes
cert-manager with its official manifest, uninstalls Istio with its CRDs, then
drains the second worker and removes it from the cluster: the virtual machine
stays up for the next lab that needs it.

```bash
dsoxlab run   k8s-servir-une-gateway-en-https
dsoxlab check k8s-servir-une-gateway-en-https
```
