# Challenge : Retrouver, compter et journaliser les flux refusés

## 📍 La situation

Dans le namespace **`livraison`** du cluster Cilium, quatre clients
(`preparation`, `expedition`, `facturation` et `retours`) appellent toutes
les deux secondes deux services, **`stock`** et **`tarif`**. Les Pods sont
répartis sur `net-w1.lab` et `net-w2.lab`. Depuis le dernier déploiement, un
client n'arrive plus à joindre l'un des deux services. Personne ne sait
lequel, ni vers quoi.

L'équipe sécurité ne veut pas qu'on touche aux politiques réseau : elle veut
que le refus soit **audité**. Un autre namespace du cluster refuse aussi des
flux, et ce n'est pas votre sujet.

Vous êtes sur le plan de contrôle `net-cp.lab`, avec `kubectl` et `helm`. Le
cluster tourne sans kube-proxy, avec Cilium 1.20.5, Hubble et ses métriques
activés (port 9965 de chaque nœud). Cilium 1.20.5 déclare prendre en charge
Kubernetes 1.33 à 1.36, et ce cluster tourne en 1.37.

## 🎯 Ce que vous devez obtenir

1. Un ConfigMap **`refus`** dans `livraison`, avec trois clés : **`source`**,
   le nom du Pod client refusé, **`destination`**, le nom du Pod qu'il ne peut
   plus joindre, et **`noeud`**, le nœud dont l'agent Cilium voit le refus.
   **Exigence bloquante.**
2. Sur ce nœud, la métrique **`hubble_drop_total`** porte une série qui nomme
   **à la fois** le Pod source et le Pod destination du flux refusé, et elle
   continue d'augmenter : le refus reste en place, et le client refusé joint
   toujours le service qui lui est permis. **Exigence bloquante.**
3. Sur ce même nœud, les flux refusés du namespace `livraison` sont journalisés
   dans **`/var/run/cilium/hubble/refus-livraison.log`**, et ce fichier ne porte
   **rien d'autre** : ni d'autres verdicts, ni les refus d'autres namespaces.

## 🧭 Les repères utiles

Une politique réseau ne s'applique pas toujours sur le nœud de la
destination.

## ✅ Comment vous saurez que c'est bon

Les tests lisent votre ConfigMap, le port de métriques du nœud du refus à
douze secondes d'intervalle, et le journal exporté sur ce nœud. Le client
refusé, sa destination et donc le nœud sont tirés au sort à la préparation.
Le seuil de réussite est de 70 %, soit les trois exigences, et les deux
exigences bloquantes doivent être tenues.

```bash
dsoxlab check k8s-challenge-retrouver-les-flux-refuses
```
