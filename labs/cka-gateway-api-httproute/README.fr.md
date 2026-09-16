# Router avec la Gateway API, et voir la Gateway se déclarer programmée

Lab **CKA**, domaine *Services and Networking* (20 % de l'épreuve), compétence
« Use the Gateway API to manage Ingress traffic ».

Jumeau de [`cka-ingress-path-routing`](../cka-ingress-path-routing/) : même
situation de départ, même preuve, et l'autre façon de la router. Les jouer
l'un après l'autre montre ce que la Gateway API change, et ce qu'elle ne
change pas.

**Le piège propre à cette API est mesuré et fait le premier test.** Une Gateway
dont le listener déclare un port ne correspondant à aucun point d'entrée du
contrôleur est **acceptée** par l'API, apparaît dans `kubectl get`, et n'est
**jamais programmée** : rien ne route, et rien ne le dit sauf ses conditions.
Le test lit donc `Programmed`, pas l'existence de l'objet.

C'est aussi pourquoi `shared/traefik.yml` aligne l'entrypoint web sur le port
**80** avec le sysctl `net.ipv4.ip_unprivileged_port_start=0` : le chart le met
sur 8000, et un candidat écrivant `port: 80`, ce que toute documentation lui
montre, verrait sa Gateway rester muette.

Mesuré le 2026-09-16, `Programmed=True` et :

| chemin | réponse |
|---|---|
| `/api` | `api` |
| `/web` | `web` |
| `/autre` | 404 |

Les deux applications répondent leur nom, avec `hashicorp/http-echo:1.0.0` :
le lab hérité servait `nginx:1.27` des deux côtés et ne pouvait donc pas
distinguer un routage inversé d'un routage correct.

CRD de la Gateway API **v1.6.2**, canal `standard`, posées par le setup et non
par le chart, qui prévient d'ailleurs qu'il cessera de les livrer.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 25 minutes |
| Leçon jumelée | [Gateway API](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/gateway-api/) |

```bash
dsoxlab run   cka-gateway-api-httproute
dsoxlab check cka-gateway-api-httproute
```

Le `cleanup.yaml` reprend les CRD **et** la `ValidatingAdmissionPolicy`
`safe-upgrades.gateway.networking.k8s.io` que `standard-install.yaml` pose
aussi : ce sont des objets de cluster, et aucun `delete crd` ne la reprend.
