# Challenge : Faire sortir le trafic d'un Pod par une passerelle d'egress

## La situation

Le cluster Cilium des hôtes `net-*` compte **trois nœuds** : `net-cp.lab`
(plan de contrôle), `net-w1.lab` et `net-w2.lab`. Cilium 1.20.5 remplace
kube-proxy, avec la **passerelle d'egress désactivée** et un masquage fait par
iptables.

Dans le namespace **`egress-demo`**, deux Pods tournent sur `net-w1.lab` :
**`sortie-controlee`** (étiquette `app: sortie-controlee`) et **`autre`**
(étiquette `app: autre`). Un partenaire n'accepte `sortie-controlee` que
depuis **une adresse connue** : celle de `net-w2.lab`.

Un serveur témoin tourne **hors** du cluster, sur une autre machine du même
réseau. Il répond par l'adresse source qu'il voit. Son URL est dans la
ConfigMap **`temoin`** d'`egress-demo` :
`kubectl -n egress-demo get configmap temoin -o jsonpath='{.data.url}'`.
Aujourd'hui, les deux Pods le joignent depuis l'adresse de `net-w1.lab`.

Vous êtes sur `net-cp.lab`, avec `kubectl` et `helm` configurés.

## Ce que vous devez obtenir

1. La **passerelle d'egress** et le **masquage BPF** sont tous deux activés,
   et chaque agent Cilium est prêt.
2. Une **CiliumEgressGatewayPolicy** sélectionne le Pod `sortie-controlee`
   d'`egress-demo`, et pas `autre`.
3. Cette politique couvre **l'adresse du témoin** dans ses destinations, et
   désigne **`net-w2.lab`**, et aucun autre nœud, comme passerelle.
4. Le témoin voit `sortie-controlee` arriver de **`net-w2.lab`**, et `autre`
   toujours de **`net-w1.lab`**.

## La méthode, pas à pas

**Activer la passerelle, avec ce qu'elle exige.** `helm upgrade cilium
cilium/cilium --version 1.20.5 -n kube-system --reuse-values --set
egressGateway.enabled=true --set bpf.masquerade=true`. Les deux valeurs vont
ensemble : avec la passerelle seule, l'agent s'arrête au démarrage en
`level=fatal`, et le DaemonSet reste à moitié déployé. Attendez les agents,
puis redémarrez l'opérateur pour qu'il lise la nouvelle configuration
(`kubectl -n kube-system rollout restart deployment/cilium-operator`).
`cilium status` dans un agent doit montrer `Masquerading: BPF`.

**Désigner le nœud passerelle.** Une politique ne nomme pas un nœud : elle
sélectionne des nœuds par étiquette. Posez une étiquette sur `net-w2.lab`
(par exemple `egress-gateway=true`).

**Écrire la politique.** Une `CiliumEgressGatewayPolicy` (portée cluster) a
trois parties : `selectors` (un `podSelector` avec l'étiquette `app` du Pod et
son namespace par l'étiquette `io.kubernetes.pod.namespace`),
`destinationCIDRs` (l'adresse du témoin en `/32`), et `egressGateway` (le
`nodeSelector` de la passerelle, et l'interface `enp1s0`).

**Vérifier depuis l'extérieur.** `kubectl -n egress-demo exec sortie-controlee
-- wget -qO- -T 5 <url>` rend la source que le témoin a vue. Dans un agent,
`cilium-dbg bpf egress list` montre ce que le datapath a appris : le nœud
passerelle porte l'adresse de sortie, les autres lui transmettent. Si le nœud
passerelle perd son étiquette, le Pod visé ne retombe pas sur son propre
nœud : ses requêtes expirent.

## Comment savoir que ça marche

Les tests lisent la configuration de Cilium et les politiques, puis font
joindre le témoin aux deux Pods : `sortie-controlee` doit arriver de
`net-w2.lab`, et `autre` de `net-w1.lab`.

```bash
dsoxlab check k8s-faire-sortir-le-trafic-par-une-passerelle
```
