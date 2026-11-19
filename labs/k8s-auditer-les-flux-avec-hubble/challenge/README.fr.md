# Challenge : Auditer les flux réseau avec Hubble

## La situation

Dans le namespace **`magasin`** du cluster Cilium, une API (`api`, sur
`net-w1.lab`) est appelée toutes les deux secondes par trois clients,
**`vitrine`**, **`panier`** et **`compta`**, tous sur `net-w2.lab`. Une
NetworkPolicy, **`api-entrant`**, protège l'API. Depuis son déploiement, l'un
des trois clients se plaint que l'API ne répond plus, et personne ne sait
lequel.

L'équipe sécurité ne veut pas qu'on lève la politique : elle veut que le refus
soit **audité**. Quel flux est refusé et pourquoi, une métrique qui compte ces
refus Pod par Pod, et un journal des refus sur le nœud, qu'on puisse
conserver.

Vous êtes sur le plan de contrôle `net-cp.lab`, avec `kubectl` et `helm`. Le
cluster tourne sans kube-proxy, avec Cilium 1.20.5, Hubble et ses métriques
activés (port 9965 de chaque nœud). Cilium 1.20.5 déclare prendre en charge
Kubernetes 1.33 à 1.36, et ce cluster tourne en 1.37.

## Ce que vous devez obtenir

1. Un ConfigMap **`constat`** dans le namespace `magasin`, avec deux clés :
   **`pod-source`**, le nom du Pod client refusé, et **`raison`**, la raison du
   refus telle que Hubble la nomme.
2. La métrique **`hubble_drop_total`** de `net-w1.lab` nomme le Pod refusé
   comme source (`source="magasin/<pod>"`), et continue d'augmenter : le refus
   reste en place.
3. Les flux refusés sont journalisés sur le nœud, dans
   **`/var/run/cilium/hubble/events.log`**, et ce fichier ne porte **que** des
   flux `DROPPED`.

## La méthode, pas à pas

**Trouver le bon agent.** Une politique d'entrée s'applique là où vit le Pod
de destination. `kubectl -n magasin get pods -o wide` montre que `api` tourne
sur `net-w1.lab` ; `kubectl -n kube-system get pods -l k8s-app=cilium -o wide`
donne l'agent Cilium de ce nœud. Chaque agent embarque le client `hubble`.

**Lire les refus.** `kubectl -n kube-system exec <agent> -c cilium-agent --
hubble observe --namespace magasin --verdict DROPPED` ne montre que les flux
refusés : Pod source, Pod de destination, port, et la raison du refus à côté
du verdict.
Avec `-o json`, la raison est le champ `drop_reason_desc`. Hubble garde aussi
les flux des passages précédents : `--since 1m` ne montre que les refus en cours,
et le client refusé change à chaque `dsoxlab run`.
`--print-raw-filters` affiche le filtre que construisent les options, qui
resservira plus bas. Consignez ce que vous avez vu :

```bash
kubectl -n magasin create configmap constat \
  --from-literal=pod-source=<pod> --from-literal=raison=<raison>
```

**Lire la métrique.** `curl -s http://<adresse de net-w1>:9965/metrics | grep
hubble_drop_total` (l'adresse : `kubectl get node net-w1.lab -o wide`). Les
séries portent la raison et le protocole, pas le Pod : elles disent que
quelque chose est refusé, pas qui. La métrique drop accepte un contexte, écrit
dans son nom dans les valeurs du chart :
`drop:sourceContext=pod;destinationContext=pod` ajoute les labels `source` et
`destination`.

**Exporter les refus.** Les valeurs `hubble.export.static` du chart écrivent
les flux dans un fichier du nœud : `enabled`, `filePath`
(`/var/run/cilium/hubble/events.log`) et `allowList`, une liste de filtres au
format qu'affiche `--print-raw-filters`. Un filtre sur le verdict ne garde que
les refus.

**Appliquer les deux changements.** Un point-virgule et des virgules passent
mal dans `--set` : écrivez un fichier de valeurs qui reprend **toute** la liste
`hubble.metrics.enabled` (un `-f` remplace une liste, il ne la complète pas)
et ajoute `hubble.export.static`. Puis, après
`helm repo add cilium https://helm.cilium.io` si votre utilisateur n'a pas
encore le dépôt :

```bash
helm upgrade cilium cilium/cilium --version 1.20.5 --namespace kube-system \
  --reuse-values -f <votre fichier> --wait
```

Le cluster redémarre les agents quand leur configuration change
(`rollOutCiliumPods`) : `kubectl -n kube-system rollout status ds/cilium`,
puis relisez la métrique et le fichier (`sudo tail` sur `net-w1.lab`, que
`ssh net-w1.lab` ouvre).

**Ne touchez pas à la politique.** Le lab audite un refus, il ne le lève pas.

## Comment vous saurez que ça marche

Les tests comparent le constat au client tiré par le setup et à la raison que
donne Hubble au moment du contrôle, lisent la métrique deux fois à douze
secondes d'écart sur `net-w1.lab`, puis le fichier d'export de ce nœud.

```bash
dsoxlab check k8s-auditer-les-flux-avec-hubble
```
