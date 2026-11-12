# Réparer un Service NodePort

Lab **CKAD**, domaine *Services and Networking* : « Use ClusterIP, NodePort,
LoadBalancer service types and endpoints ». Lab guidé de la leçon « Services »
de la formation Kubernetes.

L'application `accueil` tourne et répond son nom. Son Service NodePort a un
sélecteur qui ne vise aucun Pod, un `targetPort` faux, et un NodePort tiré au
hasard. L'apprenant le répare, et les tests le prouvent par une vraie requête
vers le NodePort de chacun des deux nœuds. Le voisin
[`ckad-expose-service`](../ckad-expose-service/) porte sur ClusterIP.
LoadBalancer reste hors lab : sans fournisseur, son adresse externe reste
`<pending>`.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm ; le worker `k8s-w1.lab` est interrogé aussi |
| Durée | environ 20 minutes |
| Leçon jumelée | [Services](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/#mettre-en-pratique) |

```bash
dsoxlab run   ckad-service-nodeport-reparer
dsoxlab check ckad-service-nodeport-reparer
```
