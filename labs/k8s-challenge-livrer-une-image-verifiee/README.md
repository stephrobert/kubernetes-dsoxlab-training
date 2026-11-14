# Let only verified images in, without guidance

Challenge of the **Supply chain** module of the Kubernetes course, in the Put
into practice section of the "Image Scanning (Grype/Trivy)" lesson: a
Deployment to pin to its digest, a Dockerfile to clear of its static analysis
findings, an image to sign with its public key published, a vulnerable image
to replace, and a cluster that must refuse unsigned images at creation. Ten
states, threshold 70, three blocking.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab sets up the `livraison` namespace, a local registry on port 5000 of the node, and Kyverno 1.19.2 with no policy |
| Duration | about 60 minutes |
| Related page | [Image Scanning (Grype/Trivy)](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/image-scanning/) |

```bash
dsoxlab run    k8s-challenge-livrer-une-image-verifiee
dsoxlab check  k8s-challenge-livrer-une-image-verifiee
dsoxlab submit k8s-challenge-livrer-une-image-verifiee
```
