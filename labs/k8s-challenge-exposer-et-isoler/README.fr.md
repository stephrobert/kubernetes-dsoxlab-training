# Exposer une application et isoler ses flux

Challenge du module **Réseau et exposition** de la formation Kubernetes, dans la
section Mettre en pratique de la leçon « Network Policies » : deux applications
routées par hôte et par chemin, un Service hérité à réparer, un Pod client dont
le DNS est cassé, et une base isolée qui garde sa sortie DNS. Sept exigences,
seuil 70, trois bloquantes.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue (Calico, Traefik) ; le lab pose les namespaces `comptoir` et `voisinage` |
| Durée | environ 45 minutes |
| Page associée | [Network Policies, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/#mettre-en-pratique) |

```bash
dsoxlab run    k8s-challenge-exposer-et-isoler
dsoxlab check  k8s-challenge-exposer-et-isoler
dsoxlab submit k8s-challenge-exposer-et-isoler
```
