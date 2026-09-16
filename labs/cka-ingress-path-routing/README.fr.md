# Router deux applications sur un seul hôte, et prouver que chacune reçoit la sienne

Lab **CKA**, domaine *Services and Networking* (20 % de l'épreuve), exposition
par Ingress.

**Le lab hérité ne pouvait rien prouver**, et c'est ce qui a motivé sa
réécriture : il servait `nginx:1.27` des **deux** côtés. Ses tests ne pouvaient
donc distinguer ni un routage inversé, ni l'absence de routage. Les deux
applications répondent ici leur propre nom, avec `hashicorp/http-echo:1.0.0`.

Le test interroge **trois** chemins, et le troisième est le contrôle : une
règle unique qui enverrait tout vers un seul service passerait les deux
premières mesures sans router quoi que ce soit.

Mesuré le 2026-09-16 :

| chemin | réponse |
|---|---|
| `/api` | `api` |
| `/web` | `web` |
| `/autre` | 404 |

**Traefik, et pas ingress-nginx** : ce dernier est archivé depuis le 24 mars
2026, et la leçon du blog a basculé. Chart `traefik/traefik` **41.6.0**,
appVersion v3.7.13, exposé en NodePort parce qu'un Service LoadBalancer
resterait `Pending` sur un cluster kubeadm sans fournisseur de cloud.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [Ingress](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ingress/) |

```bash
dsoxlab run   cka-ingress-path-routing
dsoxlab check cka-ingress-path-routing
```
