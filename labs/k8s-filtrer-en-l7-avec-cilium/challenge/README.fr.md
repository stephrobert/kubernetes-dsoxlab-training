# Challenge : Servir un Gateway et filtrer en L7 avec Cilium

## La situation

Le cluster Cilium des hôtes `net-*` compte **trois nœuds** : `net-cp.lab`,
`net-w1.lab`, `net-w2.lab`. Cilium 1.20.5 y remplace kube-proxy. Sa **Gateway
API est éteinte**, les CRD de la Gateway API ne sont pas installées, et le
cluster n'a **aucun répartiteur de charge**.

Dans le namespace **`catalogue`**, l'application **`fiches`** répond en HTTP
derrière le Service `fiches` (port 80). Le Pod **`lecteur`** (étiquette
`app: lecteur`) la lit. L'équipe veut publier `fiches` sous le nom
**`fiches.formation.test`** par un Gateway servi par Cilium, et en lecture
seule : GET oui, écriture non. Pour les adresses exposées, l'équipe réseau
vous confie **`172.30.16.0/28`**.

Vous êtes sur `net-cp.lab`, avec `kubectl` et `helm` configurés.

## Ce que vous devez obtenir

1. Un **Gateway** de classe `cilium` dans `catalogue`, avec un **listener
   HTTP sur le port 80**, est **Programmed** et a une adresse.
2. `http://fiches.formation.test/` par ce Gateway mène à `fiches`.
3. Depuis `lecteur`, `GET /` est servi et `POST /` est **refusé en 403**.
4. Par le Gateway **aussi**, `GET /` est servi et `POST /` est refusé en
   403.

## La méthode, pas à pas

**Activer la Gateway API de Cilium.** Cilium 1.20.5 exige les CRD de la
Gateway API **v1.6.3** : `kubectl apply --server-side -f
https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.3/standard-install.yaml`.
Puis `helm upgrade cilium cilium/cilium --version 1.20.5 -n kube-system
--reuse-values --set gatewayAPI.enabled=true`, attendez les agents et
redémarrez l'opérateur. La GatewayClass **`cilium`** apparaît, `Accepted`.

**Servir fiches.** Un `Gateway` avec `gatewayClassName: cilium` et un
listener `HTTP` sur le port 80, et une `HTTPRoute` qui s'y attache
(`parentRefs`), limitée au nom (`hostnames`), vers le Service `fiches`.
Cilium crée un Service de type `LoadBalancer` pour le Gateway : sans
répartiteur de charge, le Gateway reste **non Programmed**, raison
`AddressNotAssigned`. Un **`CiliumLoadBalancerIPPool`** avec le bloc
`172.30.16.0/28` permet à Cilium de lui donner une adresse. Vérifiez avec
`curl -H 'Host: fiches.formation.test' http://<adresse>/` depuis `net-cp`.

**Filtrer en L7.** Une **`CiliumNetworkPolicy`** sur les Pods de `fiches`
autorise `lecteur` (`fromEndpoints`) sur le port 5678, avec `rules.http` :
méthode `GET`, chemin `/`. Cilium fait alors passer ce trafic par son
proxy : un `POST` reçoit un **403 Access denied**.

**Penser au Gateway.** Dès que la politique s'applique, le Gateway ne répond
plus : son trafic ne vient pas de `lecteur`, il arrive avec l'**identité
réservée `ingress`** de Cilium. Ajoutez une règle d'entrée avec
`fromEntities: [ingress]` et les mêmes règles `http`. Le Gateway répond de
nouveau, et son `POST` est refusé lui aussi.

## Comment savoir que ça marche

Les tests lisent les conditions du Gateway, puis envoient de vraies
requêtes : par le Gateway, et depuis `lecteur`, en GET et en POST à chaque
fois.

```bash
dsoxlab check k8s-filtrer-en-l7-avec-cilium
```
