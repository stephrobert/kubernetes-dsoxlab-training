# Challenge : repérer les signaux clés d'un cluster et les alerter en PromQL

## 🧭 La situation

Le cluster est supervisé par **Prometheus**, qui collecte les trois sources de
la leçon : kube-state-metrics, le kubelet et cAdvisor. Il tourne dans le
namespace `supervision` et répond sur `http://localhost:30090` depuis
`k8s-cp.lab`. Il n'a encore **aucune règle d'alerte**.

Dans le namespace **`signaux`**, deux applications souffrent sans que personne
ne soit prévenu :

- `memoire-courte` est tuée régulièrement parce qu'elle dépasse sa limite de
  mémoire ;
- `calcul-serre` est freinée en permanence par sa limite CPU.

Une troisième, `temoin-calme`, a elle aussi des limites, mais ne les atteint
jamais. Elle ne doit déclencher aucune alerte.

## 🎯 Ce que vous devez obtenir

1. Une alerte nommée **`SignauxOOMKilled`** est **déclenchée** (état
   `firing`) pour le Pod de `memoire-courte`.
2. Une alerte nommée **`SignauxThrottling`** est **déclenchée** pour le Pod
   de `calcul-serre`.
3. Aucune des deux ne se déclenche pour `temoin-calme`.

## 🔎 Les repères utiles

Prometheus lit ses règles dans le ConfigMap **`prometheus-regles`** du
namespace `supervision`. Chaque clé du ConfigMap devient un fichier, et
Prometheus charge les fichiers qui finissent par `.yaml`.

Un ConfigMap modifié met environ une minute à atteindre le Pod. Prometheus ne
relit ensuite ses règles que si on le lui demande : `curl -X POST
http://localhost:30090/-/reload`.

`http://localhost:30090/api/v1/rules` montre les règles chargées et leur
santé, `http://localhost:30090/api/v1/alerts` les alertes en attente
(`pending`) et déclenchées (`firing`). Une alerte reste en attente pendant la
durée de son `for:` avant de se déclencher.

La leçon donne une requête pour chacun des cinq signaux. Testez vos
expressions sur l'API avant d'en faire des alertes : `curl -s
http://localhost:30090/api/v1/query --data-urlencode 'query=...'`.

## ✅ Comment vous saurez que c'est bon

Les tests interrogent l'API de Prometheus : ils lisent les alertes
déclenchées, et vérifient que chacune vise le bon Pod et pas le témoin.
Attendez que vos deux alertes soient en `firing` avant de lancer le contrôle.

```bash
dsoxlab check k8s-reperer-les-signaux-d-un-cluster
```
