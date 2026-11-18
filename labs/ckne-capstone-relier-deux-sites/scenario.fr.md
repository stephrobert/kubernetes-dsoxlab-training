# Capstone : relier deux sites, annoncer un Service au réseau et le servir en HTTPS

## La situation

La boutique tourne sur deux sites, chacun dans son cluster Kubernetes 1.37 d'un
seul nœud, sans kube-proxy, avec Cilium 1.20.5 :

| Site | Nœud | Contexte `kubectl` |
|---|---|---|
| site 1 | `ha-cp1.lab` | `cluster-1` (courant) |
| site 2 | `ha-cp2.lab` | `cluster-2` |

Dans chaque site, le namespace **`boutique`** porte la **vitrine**, qui répond
par le nom de son site, derrière un Service ordinaire `vitrine`. Aujourd'hui,
chaque site ne connaît que sa propre vitrine.

Les deux clusters ont été installés pour pouvoir être reliés : des
identifiants de cluster distincts, la même autorité de certification, et ce qu'il
faut côté Cilium. Ils ne le sont pas encore. Le CLI `cilium` (v0.20.3) est
installé sur `ha-cp1.lab`.

Sur le **site 1** seulement :

- le Pod **`client`** sert à vos essais ;
- le Service **`interne`**, de type LoadBalancer, est réservé à l'équipe
  d'exploitation : il ne doit **jamais** être annoncé au réseau ;
- le plan de contrôle BGP de Cilium est activé, la Gateway API (v1.6.3) est
  servie par Cilium, et cert-manager (v1.21.3) dispose d'une autorité interne,
  le ClusterIssuer **`autorite-des-sites`**.

L'équipe réseau a un routeur hors des clusters, à l'adresse **10.10.50.200**,
en AS **65000**. Il attend le site 1 comme voisin, en AS **65001**. Elle vous
réserve le bloc d'adresses **`192.168.240.0/28`**. Vous ne pouvez pas vous
connecter au routeur : les tests le liront pour vous.

Le nom public de la boutique est **`boutique.sites.test`**.

Vous travaillez sur `ha-cp1.lab`, avec `kubectl` et `helm` configurés et les
droits root par `sudo`. Aucune procédure n'est donnée, et aucun objet n'est
nommé : choisir les bons fait partie du capstone.

## Ce que vous devez obtenir

1. Depuis le client du site 1, le nom `vitrine.boutique` répond depuis **les
   deux sites**. Si le site 1 n'a plus aucun réplica de la vitrine, ce nom
   répond toujours, depuis le site 2.
2. Le routeur de l'équipe réseau joint la vitrine du **site 1** à une adresse
   du bloc réservé, qu'il a **apprise par lui-même**. Le Service `interne`
   n'est pas annoncé.
3. Les clients joignent la vitrine du site 1 à **`https://boutique.sites.test`**,
   avec un certificat émis par **cert-manager** depuis l'autorité
   `autorite-des-sites`. Une requête en **HTTP** sur ce nom est **redirigée**
   vers HTTPS, en 301.

## Comment vous serez évalué

Trois états, à poids égal, et tous **bloquants** : réussir les deux autres ne
compense pas l'échec de l'un d'eux. Le seuil est de **70 sur 100**. Le retour se
limite à la liste des critères non satisfaits, par leur libellé, et à la note :
aucun message ne dit pourquoi.

Les tests lisent les clusters, jamais vos fichiers. Ils appellent la vitrine
depuis le client, vident eux-mêmes le site 1 de ses réplicas puis les
remettent, lisent la table du routeur et l'appellent depuis lui, et vérifient
le certificat servi avec l'autorité des sites.

```bash
dsoxlab check  ckne-capstone-relier-deux-sites
dsoxlab submit ckne-capstone-relier-deux-sites
```
