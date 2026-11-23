# Challenge : répondre aux questions d'exploitation en PromQL

## 🧭 La situation

Le cluster est supervisé par **Prometheus**, qui collecte kube-state-metrics,
le kubelet et cAdvisor. Il répond sur `http://localhost:30090` depuis
`k8s-cp.lab`.

L'équipe d'exploitation prépare son tableau de bord et vous demande quatre
requêtes PromQL. Elle veut les retrouver dans le ConfigMap **`requetes`** du
namespace **`atelier-promql`**, une requête par clé.

Dans ce namespace, le Pod `relance-auto` s'arrête en erreur toutes les dix
secondes, puis redémarre.

## 🎯 Ce que vous devez obtenir

Le ConfigMap `requetes` porte ces quatre clés :

1. **`memoire-par-namespace`** : la mémoire utilisée par les conteneurs
   (`container_memory_working_set_bytes`), additionnée **par namespace**. Une
   série par namespace, avec le seul label `namespace`. Écartez les séries
   sans conteneur.
2. **`top3-cpu-pods`** : les **trois** Pods qui consomment le plus de CPU,
   mesuré sur les **5 dernières minutes**
   (`container_cpu_usage_seconds_total`). Une série par Pod, avec les labels
   `namespace` et `pod`. Écartez là aussi les séries sans conteneur.
3. **`p95-duree-api`** : le **95e percentile** de la durée des requêtes HTTP
   que Prometheus sert lui-même (`prometheus_http_request_duration_seconds`),
   sur **5 minutes**, **par handler**.
4. **`redemarrages-atelier`** : le nombre de redémarrages des conteneurs
   d'`atelier-promql` sur les **10 dernières minutes**, une série par
   conteneur, avec les labels d'origine.

## 🔎 Les repères utiles

Testez chaque requête sur l'API avant de la ranger dans le ConfigMap :

```bash
curl -s http://localhost:30090/api/v1/query --data-urlencode 'query=up' | jq '.data.result'
```

Un compteur ne se lit pas tel quel : la leçon montre la fonction qui donne un
taux par seconde, et celle qui donne une augmentation sur une durée.

Après une agrégation, seuls les labels que vous gardez restent. Un percentile
se calcule sur les buckets d'un histogramme, en gardant le label `le`.

Un ConfigMap se crée avec `kubectl create configmap ... --from-literal=clé=valeur`,
une option par clé. Mettez chaque requête entre apostrophes.

## ✅ Comment vous saurez que c'est bon

Pour chaque clé, le test évalue votre requête et une requête de référence **au
même instant**, puis compare les deux résultats série par série : mêmes
labels, mêmes valeurs. Une requête qui garde un label de trop, ou qui oublie
un filtre, rend d'autres séries et ne passe pas.

```bash
dsoxlab check k8s-interroger-prometheus-en-promql
```
