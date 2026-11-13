# Émettre des certificats avec cert-manager et une CA interne

Lab guidé de la leçon « cert-manager », module Administrer le cluster du
niveau 4 : un émetteur auto-signé, une CA interne, le certificat d'un service
signé par elle, puis un certificat cassé à diagnostiquer et réparer. cert-manager
v1.21.3, installé et retiré par le lab ; ACME public hors lab.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab pose cert-manager et le namespace `atelier-tls` |
| Durée | environ 35 minutes |
| Page associée | [cert-manager, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cert-manager/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-emettre-un-certificat-avec-cert-manager
dsoxlab check k8s-emettre-un-certificat-avec-cert-manager
```
