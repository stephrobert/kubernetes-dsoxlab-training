# Pin an image by digest and pull from a private registry

Guided lab of the **Deploy your applications** module of the Kubernetes course:
pin an image by digest, diagnose an ImagePullBackOff, and pull from a private
registry through a docker-registry Secret carried by a ServiceAccount.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `lab`; the lab sets up a private registry local to the cluster and the `galerie` namespace |
| Duration | about 30 minutes |
| Related page | [Gérer les images conteneurs, Mettre en pratique section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubernetes-images/) |

```bash
dsoxlab run   k8s-gerer-les-images
dsoxlab check k8s-gerer-les-images
```
