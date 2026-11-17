# Annoncer les Pods et les Services à un routeur en BGP

## La situation

Le cluster Cilium des hôtes `net-*` compte **trois nœuds** : `net-cp.lab`
(plan de contrôle), `net-w1.lab` et `net-w2.lab`. Cilium 1.20.5 remplace
kube-proxy, avec le **plan de contrôle BGP désactivé**.

Hors du cluster, un routeur de l'équipe réseau tourne sous **FRR 10.6.2** :
AS **65000**, adresse **10.10.50.200**. Il déclare déjà les trois nœuds comme
voisins, et les attend en AS **65001**. Pour l'instant, ses sessions restent
en `Active` : personne ne répond.

Dans le namespace **`bgp-demo`**, l'application `web` (nginx) est exposée par
le Service **`web`** de type `LoadBalancer`, étiqueté `annonce-bgp=oui`. Le
cluster n'a pas de répartiteur de charge : son adresse externe reste
`<pending>`. L'équipe réseau vous confie le bloc **`172.30.0.0/28`** pour ces
adresses.

Vous êtes sur `net-cp.lab`, avec `kubectl` et `helm` configurés. Vous ne
pouvez pas vous connecter au routeur : les tests le liront pour vous.

## Ce que vous devez obtenir

1. Le **plan de contrôle BGP** de Cilium est activé, et chaque agent est prêt.
2. Le routeur a une **session établie** avec chacun des trois nœuds.
3. Le routeur a appris le **réseau des Pods** de chaque nœud.
4. Le Service `web` a une adresse de **`172.30.0.0/28`**, et le routeur l'a
   apprise en **/32**.
5. Depuis le réseau du routeur, l'application **répond** à cette adresse.

## La méthode, pas à pas

**Activer le plan de contrôle BGP.** `helm upgrade cilium cilium/cilium
--version 1.20.5 -n kube-system --reuse-values --set
bgpControlPlane.enabled=true`, attendez les agents, puis redémarrez
l'opérateur : c'est lui qui crée les CRD BGP (`kubectl get crd | grep bgp`).

**Déclarer le pair.** Trois objets, de portée cluster, qui se citent
mutuellement :

- un **`CiliumBGPClusterConfig`** : quels nœuds parlent BGP (`nodeSelector`),
  avec quel AS local (`localASN: 65001`), vers quel pair (`peerAddress`,
  `peerASN: 65000`), et avec quel `peerConfigRef` ;
- un **`CiliumBGPPeerConfig`** : la famille d'adresses (`ipv4`, `unicast`),
  et l'étiquette des annonces à envoyer à ce pair ;
- une **`CiliumBGPAdvertisement`** qui porte cette étiquette : ce qu'il faut
  annoncer. Une entrée de type `PodCIDR`, une de type `Service` avec le type
  d'adresse `LoadBalancerIP` et un `selector` sur les étiquettes du Service.

**Donner des adresses aux Services LoadBalancer.** Un
**`CiliumLoadBalancerIPPool`** avec le bloc `172.30.0.0/28`. Le Service `web`
reçoit son adresse en quelques secondes.

**Étiqueter les nœuds.** Le `nodeSelector` de la configuration de cluster
choisit les nœuds par étiquette : posez cette étiquette sur les trois nœuds.
Sans elle, aucune session ne démarre, et aucune erreur ne le dit.

**Vérifier de votre côté.** `kubectl get ciliumbgpnodeconfigs` montre une
configuration par nœud sélectionné. Dans un agent, `cilium-dbg bgp peers`
montre l'état de la session et le nombre de routes envoyées. Un AS faux d'un
côté laisse la session en `Active`, et le routeur journalise une
`NOTIFICATION` (bad peer AS).

## Comment savoir que ça marche

Les tests lisent la configuration de Cilium, puis interrogent le
**routeur** : les trois sessions sont-elles établies, quelles routes a-t-il
apprises ? Enfin, ils demandent l'application depuis le réseau du routeur, à
l'adresse de LoadBalancer, par la route que le routeur a reçue.

```bash
dsoxlab check k8s-annoncer-un-service-en-bgp
```
