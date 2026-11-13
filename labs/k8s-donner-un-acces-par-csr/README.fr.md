# Donner un accès humain par une CertificateSigningRequest

Second lab guidé de la leçon « PKI d'un cluster Kubernetes », module Administrer
le cluster du niveau 4 : la clé et la demande de camille, l'approbation, le
certificat délivré par l'API, son kubeconfig, puis des droits de lecture sur un
namespace, vérifiés sous son identité. La clé de la CA ne sort jamais du nœud.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab pose le namespace `equipe-web` |
| Durée | environ 25 minutes |
| Page associée | [PKI du cluster, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pki-cluster-kubernetes/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-donner-un-acces-par-csr
dsoxlab check k8s-donner-un-acces-par-csr
```
