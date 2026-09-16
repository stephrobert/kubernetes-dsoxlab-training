# Router avec la Gateway API, et voir la Gateway se déclarer programmée

## La situation

Les deux mêmes applications que précédemment vivent dans le namespace **`lab`**
et servent déjà : l'API et le site, derrière `svc-api` et `svc-web`, sur le
port `80`. Un seul nom d'hôte, **`app.local`**, pour les deux.

Cette fois, l'équipe plateforme a décidé de ne plus écrire d'Ingress. Elle a
posé dans le cluster ce qu'il faut pour employer son successeur, et vous laisse
publier vos applications avec.

Chaque application répond son propre nom, ce qui vous permettra de vérifier
sans ambiguïté laquelle a répondu.

## Ce que vous devez obtenir

Pour l'hôte `app.local` :

1. Un point d'entrée HTTP existe, et le cluster le déclare **programmé**. Un
   point d'entrée accepté mais non programmé ne route rien.

2. Les requêtes dont le chemin commence par **`/api`** atteignent `svc-api`.

3. Les requêtes dont le chemin commence par **`/web`** atteignent `svc-web`.

4. Un chemin que vous n'avez pas déclaré n'atteint **ni l'une ni l'autre**.

Le contrôleur et sa classe sont déjà en place, ne les touchez pas. L'entrée
HTTP est exposée sur le port **30080** du nœud.

## Les repères utiles

Ce qui remplace l'Ingress se compose de **deux** objets, et cette séparation
est l'essentiel : l'exploitant du cluster tient le point d'entrée, les équipes
applicatives y attachent leurs routes.

```bash
kubectl get gatewayclass
kubectl api-resources --api-group=gateway.networking.k8s.io
```

Le **port** déclaré par le point d'entrée doit correspondre à un point d'entrée
du contrôleur. Sinon l'objet est accepté, apparaît dans `kubectl get`, et n'est
jamais programmé : rien ne route, et rien ne le dit sauf ses **conditions**.

Une règle de routage **sans critère de correspondance** accepte tout ce qui
arrive.

Un champ décide qui a le droit de s'attacher au point d'entrée. Les deux objets
vivant ici dans le même namespace, la valeur la plus restrictive suffit.

Les requêtes se font en indiquant à `curl` où joindre l'hôte :

```bash
curl -s --resolve app.local:30080:127.0.0.1 http://app.local:30080/api
```

## Comment vous saurez que c'est bon

Le premier test lit les **conditions** du point d'entrée, et non sa seule
existence. Le dernier interroge les **trois** chemins, le troisième servant de
contrôle.

```bash
dsoxlab check cka-gateway-api-httproute
```
