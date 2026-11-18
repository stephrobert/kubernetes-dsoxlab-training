# Relier deux clusters avec Cilium ClusterMesh

## La situation

Deux clusters Kubernetes 1.37 tournent sur **un nœud chacun**, sans
kube-proxy, avec Cilium 1.20.5 :

| Cluster | Nœud | Pods | Identifiant Cilium |
|---|---|---|---|
| `cluster-1` | `ha-cp1.lab` | `10.241.0.0/16` | 1 |
| `cluster-2` | `ha-cp2.lab` | `10.242.0.0/16` | 2 |

Ils ont été installés pour être reliés : plages de Pods et identifiants
distincts, **même autorité de certification Cilium**, et le serveur
`clustermesh-apiserver` de chacun exposé en `NodePort`. Ils ne sont **pas
encore reliés**.

Dans chaque cluster, le namespace **`mesh-demo`** contient un Deployment
`echo` qui répond par le nom de **son** cluster, derrière un Service `echo`
ordinaire. Dans `cluster-1` seulement, un Pod **`client`** dort. Aujourd'hui,
depuis `client`, `echo.mesh-demo` répond toujours `reponse-de-cluster-1`.

Vous êtes sur `ha-cp1.lab`. `kubectl` connaît **deux contextes**, `cluster-1`
(courant) et `cluster-2`, et le CLI `cilium` (v0.20.3) est installé.

## Ce que vous devez obtenir

1. L'agent Cilium de **chaque** cluster voit le nœud de l'autre.
2. Le Service `echo` de `mesh-demo` est **global** dans les **deux** clusters.
3. Depuis le Pod `client` de `cluster-1`, les **deux** clusters répondent par
   le Service `echo`.

## La méthode, pas à pas

**Regarder avant de relier.** `cilium clustermesh status --context cluster-1`
montre l'état du serveur `clustermesh-apiserver` et la façon dont il est
exposé. `kubectl --context cluster-1 -n kube-system exec ds/cilium -c
cilium-agent -- cilium-dbg node list` liste les nœuds que l'agent connaît :
le sien seulement.

**Relier.** `cilium clustermesh connect --context cluster-1
--destination-context cluster-2` relie les deux clusters **dans les deux
sens** : il donne à chacun l'adresse et les certificats pour joindre l'autre.
Puis `cilium clustermesh status --context cluster-1 --wait` attend que la
liaison soit établie. La liste des nœuds de chaque agent montre alors le nœud
distant, préfixé par le nom de son cluster.

**Rendre le Service global.** Des clusters reliés partagent leurs identités et
leurs nœuds, pas leurs Services. L'annotation `service.cilium.io/global:
"true"` sur un Service de **même nom, dans le même namespace,** des deux
côtés réunit leurs backends. Posez-la des deux côtés : d'un seul côté, l'autre
cluster ne partage pas ses backends.

**Vérifier depuis le client.** Plusieurs requêtes de `client` vers
`http://echo.mesh-demo/` doivent rendre à la fois `reponse-de-cluster-1` et
`reponse-de-cluster-2`. Dans un agent de `cluster-1`, `cilium-dbg service
list` montre les backends du Service, celui de l'autre cluster compris.

## Comment savoir que ça marche

Les tests lisent la liste des nœuds de l'agent dans chaque cluster,
l'annotation du Service `echo` des deux côtés, puis envoient douze requêtes
depuis `client` et attendent une réponse de chaque cluster.

```bash
dsoxlab check k8s-relier-deux-clusters
```
